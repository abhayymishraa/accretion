import { createContext } from "react";

// A file named in the run timeline opens in the workspace's Files panel (ChatWorkspace provides it).
export const OpenFileContext = createContext<(path: string) => void>(() => {});
