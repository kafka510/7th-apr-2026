import { FeedbackList } from './components/FeedbackList';
import { FeedbackSubmit } from './components/FeedbackSubmit';

interface FeedbackProps {
  mode?: 'list' | 'submit';
  isSuperuser?: boolean;
}

export function Feedback({ mode = 'submit', isSuperuser = false }: FeedbackProps) {
  if (mode === 'list') {
    return <FeedbackList isSuperuser={isSuperuser} />;
  }
  return <FeedbackSubmit />;
}

