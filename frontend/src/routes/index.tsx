import { createBrowserRouter, Navigate } from "react-router-dom";
import AppLayout from "../components/layout/AppLayout";
import LoginPage from "../pages/LoginPage";
import RegisterPage from "../pages/RegisterPage";
import DashboardPage from "../pages/DashboardPage";
import CreateProjectPage from "../pages/CreateProjectPage";
import ProjectWorkspace from "../pages/ProjectWorkspace";
import OutlineEditor from "../pages/OutlineEditor";
import VersionCompare from "../pages/VersionCompare";
import ExportPage from "../pages/ExportPage";
import WorldSettingPage from "../pages/WorldSettingPage";
import NotFoundPage from "../pages/NotFoundPage";

export const router = createBrowserRouter([
  // 公开路由（无 Layout 包裹）
  {
    path: "/login",
    element: <LoginPage />,
  },
  {
    path: "/register",
    element: <RegisterPage />,
  },

  // 需认证路由（包裹 AppLayout）
  {
    path: "/",
    element: <AppLayout />,
    children: [
      {
        index: true,
        element: <Navigate to="/dashboard" replace />,
      },
      {
        path: "dashboard",
        element: <DashboardPage />,
      },
      {
        path: "projects/create",
        element: <CreateProjectPage />,
      },
      // 项目工作台（包裹 WorkspaceLayout，嵌套子路由）
      {
        path: "projects/:projectId",
        element: <ProjectWorkspace />,
        children: [
          {
            index: true,
            element: <Navigate to="outline" replace />,
          },
          {
            path: "outline",
            element: <OutlineEditor />,
          },
          {
            path: "world-setting",
            element: <WorldSettingPage />,
          },
          {
            path: "compare",
            element: <VersionCompare />,
          },
          {
            path: "export",
            element: <ExportPage />,
          },
        ],
      },
    ],
  },

  // 404
  {
    path: "*",
    element: <NotFoundPage />,
  },
]);
