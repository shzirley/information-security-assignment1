import { ApplicationWizard } from '@/features/kyc/application-wizard';
export default async function Page({ params }: { params: Promise<{ id: string }> }) { const { id } = await params; return <ApplicationWizard id={id} />; }
