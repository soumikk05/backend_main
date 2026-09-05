import { useState, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { UploadCloud, FileCheck, Trash2, Image as ImageIcon } from 'lucide-react';
import { formatBytes } from '../../utils/helpers';
import './UploadZone.css';

export function UploadZone({
  label = 'Drop document here',
  hint = 'Supports JPG, PNG, BMP (up to 10MB)',
  icon: Icon = UploadCloud,
  file,
  onFileChange,
  accept = 'image/*',
}) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [previewUrl, setPreviewUrl] = useState(null);
  const inputRef = useRef(null);

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile && droppedFile.type.startsWith('image/')) {
      processFile(droppedFile);
    }
  };

  const handleChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      processFile(selectedFile);
    }
  };

  const processFile = (f) => {
    onFileChange(f);
    const url = URL.createObjectURL(f);
    setPreviewUrl(url);
  };

  const handleRemove = (e) => {
    e.stopPropagation();
    onFileChange(null);
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
      setPreviewUrl(null);
    }
    if (inputRef.current) inputRef.current.value = '';
  };

  return (
    <motion.div
      whileHover={{ scale: 1.005 }}
      whileTap={{ scale: 0.995 }}
      transition={{ duration: 0.15 }}
      className={`upload-zone ${isDragOver ? 'upload-zone--dragover' : ''} ${
        file ? 'upload-zone--has-file' : ''
      }`}
      onClick={() => inputRef.current?.click()}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        onChange={handleChange}
        className="upload-zone__input"
        tabIndex={-1}
      />

      <AnimatePresence mode="wait">
        {file ? (
          <motion.div
            key="file-info"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            transition={{ duration: 0.3 }}
            className="upload-zone__file-active"
          >
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ type: 'spring', stiffness: 500, damping: 15 }}
              className="upload-zone__active-badge"
            >
              <FileCheck size={28} className="upload-zone__check-icon" />
            </motion.div>

            <div className="upload-zone__file-info">
              <span className="upload-zone__filename">{file.name}</span>
              <span className="upload-zone__filesize">{formatBytes(file.size)}</span>
              <motion.button
                whileHover={{ scale: 1.15, backgroundColor: 'rgba(244, 63, 94, 0.25)' }}
                whileTap={{ scale: 0.9 }}
                className="upload-zone__remove"
                onClick={handleRemove}
                title="Remove file"
              >
                <Trash2 size={13} />
                <span>Remove</span>
              </motion.button>
            </div>

            {previewUrl && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="upload-zone__preview"
              >
                <img src={previewUrl} alt="Preview" />
              </motion.div>
            )}
          </motion.div>
        ) : (
          <motion.div
            key="empty-prompt"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.2 }}
          >
            <div className="upload-zone__icon-wrap">
              <Icon size={32} className="upload-zone__icon" />
            </div>
            <div className="upload-zone__label">{label}</div>
            <div className="upload-zone__hint">{hint}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
