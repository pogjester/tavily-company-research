import { Moon, Sun, Github } from "lucide-react";
import { cn } from "../lib/utils";

interface HeaderProps {
  darkMode: boolean;
  onDarkModeToggle: () => void;
}

export function Header({ darkMode, onDarkModeToggle }: HeaderProps) {
  return (
    <div className="flex justify-end items-center gap-4 mb-4">
      <a
        href="https://github.com/pogjester"
        target="_blank"
        rel="noopener noreferrer"
        className={cn(
          "p-2 rounded-full transition-colors duration-200",
          darkMode
            ? "bg-gray-700 hover:bg-gray-600 text-white"
            : "bg-white hover:bg-gray-100 text-gray-800"
        )}
      >
        <Github className="w-5 h-5" />
      </a>
      <button
        onClick={onDarkModeToggle}
        className={cn(
          "p-2 rounded-full transition-colors duration-200",
          darkMode
            ? "bg-gray-700 hover:bg-gray-600 text-yellow-400"
            : "bg-white hover:bg-gray-100 text-gray-800"
        )}
      >
        {darkMode ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
      </button>
    </div>
  );
}
