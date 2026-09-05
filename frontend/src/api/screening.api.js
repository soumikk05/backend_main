import { apiClient } from './client';

export const screeningApi = {
  /**
   * Pre-flight: Classify the document.
   */
  classifyDocument: async (documentFile) => {
    const form = new FormData();
    form.append('file', documentFile);
    const response = await apiClient.post('/api/classify-document', form, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return response.data;
  },

  /**
   * Pre-flight: Check image quality.
   */
  checkImageQuality: async (documentFile) => {
    const form = new FormData();
    form.append('file', documentFile);
    const response = await apiClient.post('/api/image-quality', form, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return response.data;
  },

  /**
   * Full Pipeline: Assess Document & Face.
   */
  assessRisk: async (documentFile, selfieFile = null) => {
    const form = new FormData();
    form.append('document_image', documentFile);
    if (selfieFile) {
      form.append('selfie_photo', selfieFile);
    }
    const response = await apiClient.post('/api/risk/assess', form, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return response.data;
  },

  /**
   * Run only OCR extraction.
   */
  extractOcr: async (documentFile) => {
    const form = new FormData();
    form.append('file', documentFile);
    const response = await apiClient.post('/api/ocr/extract', form, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return response.data;
  },

  /**
   * Run only rules validation on text.
   */
  checkValidation: async (data) => {
    // Requires JSON, not FormData usually, depending on backend. Check backend for /api/validation/check
    const response = await apiClient.post('/api/validation/check', data);
    return response.data;
  },

  /**
   * Run only tampering detection.
   */
  analyzeTampering: async (documentFile) => {
    const form = new FormData();
    form.append('file', documentFile);
    const response = await apiClient.post('/api/tampering/analyze', form, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return response.data;
  },
  
  /**
   * Run CNN forgery detection.
   */
  cnnScore: async (documentFile) => {
    const form = new FormData();
    form.append('file', documentFile);
    const response = await apiClient.post('/api/tampering/cnn-score', form, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return response.data;
  },

  /**
   * Face liveness check.
   */
  checkLiveness: async (selfieFile) => {
    const form = new FormData();
    form.append('selfie_photo', selfieFile);
    form.append('file', selfieFile);
    const response = await apiClient.post('/api/face/liveness', form, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return response.data;
  },

  /**
   * Face verification (Document vs Selfie).
   */
  verifyFace: async (documentFile, selfieFile) => {
    const form = new FormData();
    form.append('document_photo', documentFile);
    form.append('document_image', documentFile);
    form.append('selfie_photo', selfieFile);
    form.append('selfie_image', selfieFile);
    const response = await apiClient.post('/api/face/verify', form, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return response.data;
  },

  /**
   * Check backend health and ping latency.
   */
  checkHealth: async () => {
    const response = await apiClient.get('/health');
    return response.data;
  }
};
