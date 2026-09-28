import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { createRootRoute, createRoute, createRouter, Outlet, RouterProvider } from "@tanstack/react-router"

import { ChatScreen } from "@/components/ChatScreen"
import { OpsScreen } from "@/components/ops/OpsScreen"
import { LocaleProvider } from "@/i18n/LocaleProvider"

const queryClient = new QueryClient()

const rootRoute = createRootRoute({
  component: function RootLayout() {
    return <Outlet />
  },
})

const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  component: ChatScreen,
})

const opsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/ops",
  component: OpsScreen,
})

const router = createRouter({
  routeTree: rootRoute.addChildren([indexRoute, opsRoute]),
})

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router
  }
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <LocaleProvider>
        <RouterProvider router={router} />
      </LocaleProvider>
    </QueryClientProvider>
  )
}
