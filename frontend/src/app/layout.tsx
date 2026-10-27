import type { Metadata } from 'next';
import '@fontsource/inter/400.css';
import '@fontsource/inter/500.css';
import '@fontsource/inter/600.css';
import '@fontsource/inter/700.css';
import '@fontsource/montserrat/500.css';
import '@fontsource/montserrat/600.css';
import '@fontsource/montserrat/700.css';
import '@fontsource/fira-code/400.css';
import './globals.css';
import { Providers } from '@/components/providers';

export const metadata: Metadata = { title: { default: 'VELTRIX | BankKYC', template: '%s | VELTRIX' }, description: 'Simulasi pengajuan KYC dengan bukti sintetis, akses berbasis peran, dan laboratorium kriptografi akademik.' };
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="id" suppressHydrationWarning><head><script dangerouslySetInnerHTML={{ __html: "try{document.documentElement.dataset.theme=localStorage.getItem('veltrix-theme')==='dark'?'dark':'light'}catch{}" }} /></head><body><Providers>{children}</Providers></body></html>;
}
