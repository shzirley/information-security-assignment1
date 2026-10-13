'use client';

import Link from 'next/link';
import { ArrowUpRight } from 'lucide-react';
import { bytes, categoryLabels, dateLabel, type VaultFile } from '@/lib/contracts';
import { CipherLabels, FileGlyph } from '@/components/ui';

export function FileList({ files, recent = false }: { files: VaultFile[]; recent?: boolean }) {
  return <><div className="file-table-desktop"><table className="data-table file-table"><thead><tr><th>Nama file</th><th>Ukuran asli</th>{!recent && <th>Storage tiga versi</th>}<th>Tiga versi</th><th>Tanggal</th><th><span className="sr-only">Aksi</span></th></tr></thead><tbody>{files.map(file => <tr key={file.id}><td><Link href={`/vault/${file.id}`} className="file-name-link"><FileGlyph category={file.category} /><span><strong>{file.display_name}</strong><small>{categoryLabels[file.category]}</small></span></Link></td><td className="mono">{bytes(file.original_bytes)}</td>{!recent && <td className="mono">{bytes(file.total_stored_bytes)}</td>}<td><CipherLabels /></td><td className="muted">{dateLabel(file.created_at)}</td><td><Link href={`/vault/${file.id}`} className="icon-button" aria-label={`Detail ${file.display_name}`}><ArrowUpRight size={18} /></Link></td></tr>)}</tbody></table></div><div className="file-list-mobile">{files.map(file => <Link key={file.id} href={`/vault/${file.id}`} className="mobile-file-row"><div className="mobile-file-top"><FileGlyph category={file.category} /><div><strong>{file.display_name}</strong><span>{categoryLabels[file.category]} · {bytes(file.original_bytes)}</span></div><ArrowUpRight size={19} aria-hidden="true" /></div><div className="mobile-file-bottom"><CipherLabels /><span>{dateLabel(file.created_at)}</span></div></Link>)}</div></>;
}
