import { createBrowserRouter, RouterProvider, Navigate } from 'react-router-dom'
import { AppLayout } from '@/components/layout/AppLayout'
import { AnimalHistory } from '@/pages/AnimalHistory'
import { LotStatus } from '@/pages/LotStatus'
import { Adg } from '@/pages/Adg'
import { Upload } from '@/pages/Upload'

const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    children: [
      { index: true, element: <Navigate to="/history" replace /> },
      { path: 'history', element: <AnimalHistory /> },
      { path: 'lot', element: <LotStatus /> },
      { path: 'adg', element: <Adg /> },
      { path: 'upload', element: <Upload /> },
    ],
  },
])

export default function App() {
  return <RouterProvider router={router} />
}
