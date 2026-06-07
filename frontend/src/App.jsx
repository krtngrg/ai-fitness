import { Routes, Route } from "react-router-dom";

import Landing from "./pages/Landing.jsx";
import Login from "./pages/Login.jsx";
import Register from "./pages/Register.jsx";
import GoalPlanner from "./pages/GoalPlanner.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import WorkoutHistory from "./pages/WorkoutHistory.jsx";
import Profile from "./pages/Profile.jsx";
import ExerciseSelection from "./pages/ExerciseSelection.jsx";
import LiveWorkout from "./pages/LiveWorkout.jsx";
import WorkoutResults from "./pages/WorkoutResults.jsx";
import ProtectedRoute from "./components/ProtectedRoute.jsx";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />

      <Route path="/goal-planner" element={<ProtectedRoute><GoalPlanner /></ProtectedRoute>} />
      <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
      <Route path="/workout-history" element={<ProtectedRoute><WorkoutHistory /></ProtectedRoute>} />
      <Route path="/profile" element={<ProtectedRoute><Profile /></ProtectedRoute>} />
      <Route path="/exercise-selection" element={<ProtectedRoute><ExerciseSelection /></ProtectedRoute>} />
      <Route path="/live-workout" element={<ProtectedRoute><LiveWorkout /></ProtectedRoute>} />
      <Route path="/workout-results" element={<ProtectedRoute><WorkoutResults /></ProtectedRoute>} />
    </Routes>
  );
}
