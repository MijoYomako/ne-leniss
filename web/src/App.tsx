import { useEffect } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { initTelegram } from "./lib/tg";
import { Home } from "./pages/Home";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
});

function App() {
  useEffect(() => {
    initTelegram();
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <Home />
    </QueryClientProvider>
  );
}

export default App;
