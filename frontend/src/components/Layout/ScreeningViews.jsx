import { useLocation } from 'react-router-dom';
import { PipelineScreen } from '../Modules/PipelineScreen';
import { OcrScreen } from '../Modules/OcrScreen';
import { ValidationScreen } from '../Modules/ValidationScreen';
import { TamperingScreen } from '../Modules/TamperingScreen';
import { FaceScreen } from '../Modules/FaceScreen';

export function ScreeningViews() {
  const location = useLocation();
  const path = location.pathname;

  return (
    <>
      <div style={{ display: (path === '/' || path === '/pipeline') ? 'block' : 'none' }}>
        <PipelineScreen />
      </div>
      <div style={{ display: path === '/ocr' ? 'block' : 'none' }}>
        <OcrScreen />
      </div>
      <div style={{ display: path === '/validation' ? 'block' : 'none' }}>
        <ValidationScreen />
      </div>
      <div style={{ display: path === '/tampering' ? 'block' : 'none' }}>
        <TamperingScreen />
      </div>
      <div style={{ display: path === '/face' ? 'block' : 'none' }}>
        <FaceScreen />
      </div>
    </>
  );
}
