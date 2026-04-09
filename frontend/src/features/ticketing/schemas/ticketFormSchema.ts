import { z } from 'zod';

/**
 * Zod schema for TicketForm validation
 * Matches the TicketFormData type structure
 */
export const ticketFormSchema = z.object({
  title: z.string().min(1, 'Title is required').trim(),
  description: z.string().min(1, 'Description is required').trim(),
  asset_code: z.string().min(1, 'Site selection is required'),
  location: z.string().optional(),
  device_type: z.string().min(1, 'Device type selection is required'),
  device_id: z.string().min(1, 'Device selection is required'),
  sub_device_id: z.string().optional(),
  category: z.string().min(1, 'Category is required'),
  sub_category: z.string().optional(),
  loss_category: z.string().optional(),
  loss_value: z.number().min(0, 'Loss value cannot be negative').optional().or(z.literal('')),
  priority: z.string().min(1, 'Priority is required'),
  assigned_to: z.string().optional(),
  watchers: z.array(z.string()),
});

export type TicketFormSchemaType = z.infer<typeof ticketFormSchema>;

