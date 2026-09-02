"""
Region-Aware Dual-Scale Forgery Model Architecture & Evaluation Structures.

Architecture Concept:
                   DOCUMENT
                      |
         +------------+------------+
         |                         |
         v                         v
   GLOBAL BRANCH              REGION BRANCH
   full document              field crops
   resize 128x128              resize each crop 128x128
         |                         |
    MobileNetV2               MobileNetV2
         |                         |
         +------------+------------+
                      |
                   fusion
                      |
               forgery score

Supports field-level predictions:
- global_score
- dob_score
- name_score
- document_number_score
- photo_score
- other_region_scores
- final_score (configurable weighted or max-pooling fusion)

NOTE: Architecture and DataLoader ready. NO TRAINING IS EXECUTED.
"""

from typing import Dict, List, Optional, Tuple, Union
import torch
import torch.nn as nn
from torchvision import models, transforms
from torch.utils.data import Dataset, DataLoader
from PIL import Image
import numpy as np


class ForgeryBranch(nn.Module):
    """MobileNetV2 feature extractor and classification head for 128x128 inputs."""
    def __init__(self, pretrained: bool = True, dropout: float = 0.3):
        super().__init__()
        try:
            backbone = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.DEFAULT if pretrained else None)
        except Exception:
            backbone = models.mobilenet_v2(pretrained=pretrained)
        
        self.features = backbone.features
        in_features = backbone.classifier[1].in_features
        self.head = nn.Sequential(
            nn.Dropout(p=dropout),
            nn.Linear(in_features, 64),
            nn.ReLU(inplace=True),
            nn.Linear(64, 1),
            nn.Sigmoid(),
        )

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        # x: (B, 3, 128, 128)
        feat = self.features(x)
        feat = nn.functional.adaptive_avg_pool2d(feat, (1, 1)).flatten(1)
        score = self.head(feat)
        return score, feat


class RegionAwareDualScaleForgeryModel(nn.Module):
    """
    Dual-Scale Region-Aware Architecture.
    Processes full document (global branch) and high-resolution localized field crops (region branch).
    Combines outputs via configurable fusion (max-pooling, attention, or weighted combination).
    """
    def __init__(
        self,
        default_fusion_mode: str = "configurable_weights",
        weights: Optional[Dict[str, float]] = None,
    ):
        super().__init__()
        self.global_branch = ForgeryBranch(pretrained=True)
        self.region_branch = ForgeryBranch(pretrained=True)

        self.fusion_mode = default_fusion_mode

        # Configurable weights (can be tuned or set dynamically)
        self.weights = weights or {
            "global": 0.30,
            "dob": 0.20,
            "document_number": 0.20,
            "name": 0.15,
            "photo": 0.15,
            "other": 0.10,
        }

    def forward(
        self,
        global_img: torch.Tensor,
        region_crops: Optional[Dict[str, torch.Tensor]] = None,
    ) -> Dict[str, Union[torch.Tensor, float]]:
        """
        Args:
            global_img: Tensor of shape (B, 3, 128, 128) representing full document.
            region_crops: Dict mapping field_name ('dob', 'document_number', etc.)
                          to Tensor of shape (B, 3, 128, 128).
        Returns:
            Dict containing individual scores and fused final_score.
        """
        global_score, _ = self.global_branch(global_img)
        outputs = {"global_score": global_score}

        region_scores = {}
        if region_crops:
            for field_name, crop_tensor in region_crops.items():
                r_score, _ = self.region_branch(crop_tensor)
                outputs[f"{field_name}_score"] = r_score
                region_scores[field_name] = r_score

        # Multi-region fusion
        if self.fusion_mode == "max_pooling":
            all_scores = [global_score] + list(region_scores.values())
            outputs["final_score"] = torch.stack(all_scores, dim=-1).max(dim=-1).values
        else:
            # Weighted combination with fallback normalization
            weighted_sum = global_score * self.weights.get("global", 0.30)
            total_weight = self.weights.get("global", 0.30)

            for fn, sc in region_scores.items():
                w = self.weights.get(fn, self.weights.get("other", 0.10))
                weighted_sum = weighted_sum + sc * w
                total_weight += w

            outputs["final_score"] = weighted_sum / max(total_weight, 1e-6)

        return outputs


class DualScaleForgeryDataset(Dataset):
    """
    DataLoader supporting synchronized global images and extracted field crops.
    """
    def __init__(
        self,
        records: List[dict],
        global_transform=None,
        crop_transform=None,
    ):
        self.records = records
        self.global_transform = global_transform or transforms.Compose([
            transforms.Resize((128, 128)),
            transforms.ColorJitter(brightness=0.1, contrast=0.1),
            transforms.RandomRotation(degrees=2),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ])
        self.crop_transform = crop_transform or transforms.Compose([
            transforms.Resize((128, 128)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ])

    def __len__(self):
        return len(self.records)

    def __getitem__(self, idx):
        item = self.records[idx]
        global_img = Image.open(item["global_path"]).convert("RGB")
        global_t = self.global_transform(global_img)

        crop_tensors = {}
        for fn, cp in item.get("crops", {}).items():
            crop_img = Image.open(cp).convert("RGB")
            crop_tensors[fn] = self.crop_transform(crop_img)

        label = torch.tensor(item["label"], dtype=torch.float32)
        return global_t, crop_tensors, label
