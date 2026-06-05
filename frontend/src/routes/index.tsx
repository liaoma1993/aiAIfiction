import { createBrowserRouter, Navigate } from 'react-router-dom';
import AppLayout from '@/components/layout/AppLayout';
import DashboardPage from '@/pages/DashboardPage';
import CreateProjectPage from '@/pages/CreateProjectPage';
import ProjectWizardPage from '@/pages/ProjectWizardPage';
import WorkbenchPage from '@/pages/WorkbenchPage';
import NovelPreviewPage from '@/pages/NovelPreviewPage';
import CharactersPage from '@/pages/CharactersPage';
import WorldSettingPage from '@/pages/WorldSettingPage';
import FactionsPage from '@/pages/FactionsPage';
import OutlinePage from '@/pages/OutlinePage';
import NarrativeGraphPage from '@/pages/NarrativeGraphPage';
import RelationshipPage from '@/pages/RelationshipPage';
import MemoryCenterPage from '@/pages/MemoryCenterPage';
import StoryGraphPage from '@/pages/StoryGraphPage';
import LandscapePage from '@/pages/LandscapePage';
import QualityDashboardPage from '@/pages/QualityDashboardPage';
import LoginPage from '@/pages/LoginPage';
import NotFoundPage from '@/pages/NotFoundPage';
import ProvidersPage from '@/pages/ProvidersPage';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: 'dashboard', element: <DashboardPage /> },
      { path: 'projects/create', element: <CreateProjectPage /> },
      {
        path: 'projects/:projectId',
        children: [
          { index: true, element: <WorkbenchPage /> },
          { path: 'preview', element: <NovelPreviewPage /> },
          { path: 'wizard', element: <ProjectWizardPage /> },
          { path: 'characters', element: <CharactersPage /> },
          { path: 'world-setting', element: <WorldSettingPage /> },
          { path: 'factions', element: <FactionsPage /> },
          { path: 'outline', element: <OutlinePage /> },
          { path: 'narrative-graph', element: <NarrativeGraphPage /> },
          { path: 'relationships', element: <RelationshipPage /> },
          { path: 'memory-center', element: <MemoryCenterPage /> },
          { path: 'story-graph', element: <StoryGraphPage /> },
          { path: 'landscape', element: <LandscapePage /> },
          { path: 'quality-dashboard', element: <QualityDashboardPage /> },
        ],
      },
      { path: '/settings/providers', element: <ProvidersPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
  { path: '/login', element: <LoginPage /> },
]);
