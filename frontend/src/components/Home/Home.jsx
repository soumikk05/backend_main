import React from 'react';
import { HeroSection } from './HeroSection';
import { IdentraConnect } from './IdentraConnect';
import { ScreeningModularWorkspace } from '../Modules/ScreeningModularWorkspace';
import { useAuth } from '../../hooks/useAuth';

export const Home = () => {
  const { user } = useAuth();

  return (
    <main className="app__main">
      <HeroSection />
      {/* 5 Core Screening Modules & Risk Pipeline — Restricted to authorized users */}
      {user && (
        <ScreeningModularWorkspace defaultModule="pipeline" />
      )}
      {/* Interactive National Security & Citizen Engagement Section */}
      <IdentraConnect />
    </main>
  );
};
