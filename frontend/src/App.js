import { useEffect } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import Dashboard from "@/pages/Dashboard";
import "@/App.css";

function App() {
  useEffect(() => {
    document.documentElement.classList.add("dark");
    document.title = "TokenScope · Token Consumption Tracker";
  }, []);

  return (
    <div className="App grain min-h-screen bg-black text-white">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Dashboard />} />
        </Routes>
      </BrowserRouter>
      <Toaster
        theme="dark"
        position="bottom-left"
        toastOptions={{
          style: {
            background: "#0A0A0A",
            border: "1px solid #27272A",
            color: "#FFFFFF",
            borderRadius: 0,
            fontFamily: "JetBrains Mono, monospace",
            fontSize: 12,
          },
        }}
      />
    </div>
  );
}

export default App;
