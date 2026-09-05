import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'motion/react';
import { ScreeningModulesSidebar } from './ScreeningModulesSidebar';
import { PipelineScreen } from './PipelineScreen';
import { OcrScreen } from './OcrScreen';
import { ValidationScreen } from './ValidationScreen';
import { TamperingScreen } from './TamperingScreen';
import { FaceScreen } from './FaceScreen';
import './ScreeningModularWorkspace.css';

export function ScreeningModularWorkspace({ defaultModule = 'pipeline' }) {
  const location = useLocation();
  const navigate = useNavigate();

  // Determine active module based on current pathname or state
  const getModuleFromPath = (path) => {
    if (path.includes('/ocr')) return 'ocr';
    if (path.includes('/validation')) return 'validation';
    if (path.includes('/tampering')) return 'tampering';
    if (path.includes('/face')) return 'face';
    return 'pipeline';
  };

  const [activeModule, setActiveModule] = useState(getModuleFromPath(location.pathname) || defaultModule);

  useEffect(() => {
    const matched = getModuleFromPath(location.pathname);
    if (matched && matched !== activeModule) {
      setActiveModule(matched);
    }
  }, [location.pathname]);

  const handleSelectModule = (modId) => {
    setActiveModule(modId);
    // Smoothly update location path
    if (modId === 'pipeline') {
      if (location.pathname !== '/' && location.pathname !== '/pipeline') {
        navigate('/pipeline');
      }
    } else {
      navigate(`/${modId}`);
    }
  };

  return (
    <div className="screening-workspace" id="screening-workspace">
      <div className="screening-workspace__container">
        {/* Left: 5 Screening Modules Navigation Panel (from previous UI) */}
        <ScreeningModulesSidebar
          activeId={activeModule}
          onSelectModule={handleSelectModule}
        />

        {/* Right: Active Model Screening Viewport */}
        <div className="screening-workspace__viewport">
          <AnimatePresence mode="wait">
            <motion.div
              key={activeModule}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.25 }}
              className="screening-workspace__module-wrapper"
            >
              {activeModule === 'pipeline' && <PipelineScreen />}
              {activeModule === 'ocr' && <OcrScreen />}
              {activeModule === 'validation' && <ValidationScreen />}
              {activeModule === 'tampering' && <TamperingScreen />}
              {activeModule === 'face' && <FaceScreen />}
            </motion.div>
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
