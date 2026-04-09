import { TicketForm } from './components/TicketForm';

const TicketEdit = () => {
  const root = document.getElementById('react-root');
  const ticketId = root?.dataset.ticketId ?? null;
  return <TicketForm mode="edit" ticketId={ticketId} />;
};

export default TicketEdit;

