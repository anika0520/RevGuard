import { WarRoom } from "@/components/warroom/WarRoom";

export default function CampaignDetailPage({ params }: { params: { id: string } }) {
  return <WarRoom campaignId={params.id} />;
}
