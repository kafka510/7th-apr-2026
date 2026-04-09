import type { Preview } from '@storybook/react-vite';
import { Fragment } from 'react';

import '../src/index.css';

const preview: Preview = {
  parameters: {
    backgrounds: {
      default: 'dark',
      values: [
        { name: 'dark', value: '#0f172a' },
        { name: 'light', value: '#f8fafc' },
      ],
    },
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/i,
      },
    },
    a11y: {
      test: 'todo',
    },
  },
  decorators: [
    (Story) => {
      return (
        <Fragment>
          <div className="min-h-screen bg-slate-950 text-slate-100">
            <Story />
          </div>
        </Fragment>
      );
    },
  ],
};

export default preview;
