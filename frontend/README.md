# LearnMate Frontend

The Next.js-based frontend for the LearnMate application, providing a responsive and modern user interface.

## Technology Stack

- **Framework**: Next.js
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **State Management**: React Context/Hooks

## Local Development Setup

### Prerequisites

- Node.js 18+
- npm or yarn
- Backend API running (see backend README)

### Installation

1. Install dependencies:
   ```bash
   npm install
   # or
   yarn install
   ```

2. Set up environment variables:
   Create a `.env.local` file in the frontend directory:
   ```
   NEXT_PUBLIC_API_URL=http://localhost:8002
   ```

### Running the Frontend

Start the development server:
```bash
npm run dev
# or
yarn dev
```

The application will be available at http://localhost:3000

### Building for Production

```bash
npm run build
# or
yarn build
```

To start the production server:
```bash
npm start
# or
yarn start
```

## Docker Setup

The frontend can also be run via Docker:

```bash
# From the project root directory
docker-compose up frontend
```

This will start the frontend service configured to connect with the backend.

## Project Structure

- `src/`: Source code
  - `pages/`: Next.js pages
  - `components/`: React components
  - `styles/`: CSS/Tailwind styles
  - `hooks/`: Custom React hooks
  - `utils/`: Utility functions
  - `contexts/`: React contexts
  - `types/`: TypeScript type definitions
- `public/`: Static assets
- `package.json`: Dependencies and scripts

## Features

- User authentication
- Study session management
- Learning resource recommendations
- Progress tracking
- Personalized learning experience

## Dependencies

See `package.json` for a full list of dependencies.

## Browser Support

- Latest versions of Chrome, Firefox, Safari, and Edge 