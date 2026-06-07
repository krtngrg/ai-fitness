import { createContext, useContext, useEffect, useState } from "react";
import { getMe, logout as apiLogout } from "../api/client.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(undefined); // undefined = loading

  useEffect(() => {
    getMe()
      .then((data) => setUser({ id: data.id, email: data.email, name: data.name }))
      .catch(() => setUser(null));
  }, []);

  async function logout() {
    await apiLogout().catch(() => {});
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, setUser, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
