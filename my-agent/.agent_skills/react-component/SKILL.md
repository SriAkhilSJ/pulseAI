---
name: react-component
description: Build React components with TypeScript and Tailwind
---
When the user asks for a React component:
1. Use functional components with hooks, never classes
2. Export both default and named exports (e.g. `export default LoginForm; export { LoginForm };`)
3. Include TypeScript interfaces for all props (e.g. `interface Props { ... }`)
4. Use Tailwind utility classes; never inline styles
