import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface PlaceholderBlockProps {
  title: string;
  description: string;
}

export default function PlaceholderBlock({ title, description }: PlaceholderBlockProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground">{description}</p>
      </CardContent>
    </Card>
  );
}
