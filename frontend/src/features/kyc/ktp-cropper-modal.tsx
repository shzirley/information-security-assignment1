'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import * as DialogPrimitive from '@radix-ui/react-dialog';
import {
  Camera,
  Check,
  Maximize2,
  Minus,
  Plus,
  RefreshCw,
  RotateCw,
  X,
  ZoomIn,
  ZoomOut,
} from 'lucide-react';
import { Button } from '@/components/ui';

interface KtpCropperModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  file: File | null;
  onApply: (croppedFile: File, previewUrl: string) => void;
}

export function KtpCropperModal({ open, onOpenChange, file, onApply }: KtpCropperModalProps) {
  const [imageSrc, setImageSrc] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1);
  const [rotation, setRotation] = useState(0);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [imageNaturalSize, setImageNaturalSize] = useState({ width: 0, height: 0 });

  const containerRef = useRef<HTMLDivElement>(null);
  const imgRef = useRef<HTMLImageElement>(null);

  // KTP Viewfinder frame: 340px x 214px (standard ID-1 card aspect ratio 85.6 : 54)
  const frameWidth = 340;
  const frameHeight = 214;

  // Calculate natural dimensions respecting rotation
  const isSideways = rotation % 180 !== 0;
  const naturalW = isSideways ? imageNaturalSize.height || 1 : imageNaturalSize.width || 1;

  // Auto-fit scale factor: scales any high-res camera photo (e.g. 3000px) down to fit the frame width
  const baseScale = imageNaturalSize.width > 0 ? frameWidth / naturalW : 0.25;

  // Load image object URL whenever file changes
  useEffect(() => {
    if (!file) {
      setImageSrc(null);
      return;
    }
    const url = URL.createObjectURL(file);
    setImageSrc(url);
    setZoom(1);
    setRotation(0);
    setOffset({ x: 0, y: 0 });

    return () => {
      URL.revokeObjectURL(url);
    };
  }, [file]);

  const onImageLoad = (e: React.SyntheticEvent<HTMLImageElement>) => {
    const img = e.currentTarget;
    setImageNaturalSize({ width: img.naturalWidth, height: img.naturalHeight });
    setZoom(1);
    setOffset({ x: 0, y: 0 });
  };

  // Mouse / Touch drag handlers for panning
  const handleMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);
    setDragStart({ x: e.clientX - offset.x, y: e.clientY - offset.y });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;
    setOffset({
      x: e.clientX - dragStart.x,
      y: e.clientY - dragStart.y,
    });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  // Mouse wheel zoom
  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY * -0.0015;
    setZoom(prev => Math.min(3.0, Math.max(0.2, Number((prev + delta).toFixed(2)))));
  };

  // Touch support for mobile devices
  const handleTouchStart = (e: React.TouchEvent) => {
    if (e.touches.length === 1) {
      const t = e.touches[0];
      setIsDragging(true);
      setDragStart({ x: t.clientX - offset.x, y: t.clientY - offset.y });
    }
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    if (!isDragging || e.touches.length !== 1) return;
    const t = e.touches[0];
    setOffset({
      x: t.clientX - dragStart.x,
      y: t.clientY - dragStart.y,
    });
  };

  const handleTouchEnd = () => {
    setIsDragging(false);
  };

  const handleRotate = () => {
    setRotation(prev => (prev + 90) % 360);
  };

  const handleReset = () => {
    setZoom(1);
    setRotation(0);
    setOffset({ x: 0, y: 0 });
  };

  const handleFit = () => {
    setZoom(1);
    setOffset({ x: 0, y: 0 });
  };

  // Execution: Render cropped 856x540 canvas (ID-1 KTP standard)
  const handleCropAndApply = useCallback(() => {
    if (!file || !imageSrc || !containerRef.current || !imgRef.current) return;

    const targetWidth = 856;
    const targetHeight = 540;

    const canvas = document.createElement('canvas');
    canvas.width = targetWidth;
    canvas.height = targetHeight;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = 'high';
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, targetWidth, targetHeight);

    const ratio = targetWidth / frameWidth;
    const canvasScale = baseScale * zoom * ratio;

    const img = imgRef.current;

    ctx.save();
    ctx.translate(targetWidth / 2 + offset.x * ratio, targetHeight / 2 + offset.y * ratio);
    ctx.rotate((rotation * Math.PI) / 180);
    ctx.scale(canvasScale, canvasScale);
    ctx.drawImage(img, -img.naturalWidth / 2, -img.naturalHeight / 2);
    ctx.restore();

    canvas.toBlob(
      blob => {
        if (!blob) return;
        const croppedFile = new File([blob], file.name.replace(/\.[^.]+$/, '') + '-ktp.png', {
          type: 'image/png',
          lastModified: Date.now(),
        });
        const previewUrl = URL.createObjectURL(blob);
        onApply(croppedFile, previewUrl);
        onOpenChange(false);
      },
      'image/png',
      0.95
    );
  }, [file, imageSrc, baseScale, zoom, offset, rotation, onApply, onOpenChange]);

  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="modal-overlay" />
        <DialogPrimitive.Content
          className="modal-content"
          style={{
            maxWidth: '480px',
            padding: 0,
            overflow: 'hidden',
            borderRadius: 'var(--radius, 12px)',
            background: 'var(--surface)',
            color: 'var(--foreground)',
            border: '1px solid var(--border)',
            boxShadow: '0 16px 48px rgba(0, 0, 0, 0.22)',
          }}
        >
          {/* Modal Header */}
          <div
            style={{
              padding: '16px 22px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              borderBottom: '1px solid var(--border)',
              background: 'var(--surface)',
            }}
          >
            <div>
              <DialogPrimitive.Title
                style={{
                  fontSize: '16px',
                  fontWeight: 600,
                  color: 'var(--foreground)',
                  margin: 0,
                }}
              >
                Paskan Foto KTP
              </DialogPrimitive.Title>
              <DialogPrimitive.Description
                style={{
                  fontSize: '12px',
                  color: 'var(--muted)',
                  margin: '3px 0 0',
                }}
              >
                Geser dan sesuaikan foto agar pas di dalam bingkai kartu
              </DialogPrimitive.Description>
            </div>
            <DialogPrimitive.Close asChild>
              <button className="icon-button" aria-label="Tutup" style={{ minWidth: '36px', minHeight: '36px' }}>
                <X size={18} />
              </button>
            </DialogPrimitive.Close>
          </div>

          {/* Viewfinder Canvas Area */}
          <div
            style={{
              position: 'relative',
              width: '100%',
              height: '320px',
              background: '#0b132b',
              overflow: 'hidden',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              userSelect: 'none',
              cursor: isDragging ? 'grabbing' : 'grab',
            }}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
            onWheel={handleWheel}
            onTouchStart={handleTouchStart}
            onTouchMove={handleTouchMove}
            onTouchEnd={handleTouchEnd}
          >
            {/* The Image with Auto-fit baseScale */}
            {imageSrc && (
              <img
                ref={imgRef}
                src={imageSrc}
                alt="Sumber Foto KTP"
                onLoad={onImageLoad}
                style={{
                  position: 'absolute',
                  maxWidth: 'none',
                  maxHeight: 'none',
                  pointerEvents: 'none',
                  transform: `translate(${offset.x}px, ${offset.y}px) rotate(${rotation}deg) scale(${baseScale * zoom})`,
                  transformOrigin: 'center center',
                  transition: isDragging ? 'none' : 'transform 0.08s ease-out',
                }}
              />
            )}

            {/* CUTOUT VIEWFINDER: KTP FRAME (340px x 214px) */}
            <div
              ref={containerRef}
              style={{
                position: 'relative',
                width: `${frameWidth}px`,
                height: `${frameHeight}px`,
                pointerEvents: 'none',
                borderRadius: '10px',
                border: '2.5px solid var(--primary, #2563eb)',
                boxShadow: '0 0 0 9999px rgba(11, 19, 43, 0.72)',
                boxSizing: 'border-box',
              }}
            >
              {/* NIK Box Guide */}
              <div
                style={{
                  position: 'absolute',
                  top: '18%',
                  left: '6%',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                }}
              >
                <span
                  style={{
                    fontSize: '11px',
                    fontWeight: 700,
                    color: 'var(--primary, #2563eb)',
                    background: 'rgba(37, 99, 235, 0.15)',
                    padding: '1px 4px',
                    borderRadius: '3px',
                    letterSpacing: '0.5px',
                  }}
                >
                  NIK
                </span>
                <div
                  style={{
                    width: '135px',
                    height: '18px',
                    border: '1.5px dashed var(--primary, #2563eb)',
                    borderRadius: '4px',
                    background: 'rgba(37, 99, 235, 0.1)',
                  }}
                />
              </div>

              {/* Photo Box Guide */}
              <div
                style={{
                  position: 'absolute',
                  top: '19%',
                  right: '6%',
                  width: '68px',
                  height: '94px',
                  border: '1.5px dashed var(--primary, #2563eb)',
                  borderRadius: '6px',
                  background: 'rgba(37, 99, 235, 0.1)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <span
                  style={{
                    fontSize: '9px',
                    color: 'var(--primary, #2563eb)',
                    fontWeight: 600,
                    letterSpacing: '0.3px',
                  }}
                >
                  FOTO
                </span>
              </div>
            </div>
          </div>

          {/* Instruction Caption */}
          <div
            style={{
              padding: '8px 16px 4px',
              textAlign: 'center',
              fontSize: '12px',
              color: 'var(--muted)',
              background: 'var(--surface)',
            }}
          >
            Tempatkan KTP di dalam area yang tersedia.
          </div>

          {/* Interactive Controls Bar */}
          <div
            style={{
              padding: '14px 22px 18px',
              display: 'flex',
              flexDirection: 'column',
              gap: '14px',
              borderTop: '1px solid var(--border)',
              background: 'var(--surface-subtle)',
            }}
          >
            {/* Zoom Controls: Minus, Slider, Plus, Value */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <button
                type="button"
                className="button button-secondary"
                onClick={() => setZoom(z => Math.max(0.2, Number((z - 0.1).toFixed(2))))}
                style={{ minHeight: '34px', padding: '0 8px' }}
                aria-label="Zoom Out"
              >
                <Minus size={14} />
              </button>

              <input
                type="range"
                min="0.2"
                max="2.5"
                step="0.02"
                value={zoom}
                onChange={e => setZoom(parseFloat(e.target.value))}
                style={{
                  flex: 1,
                  accentColor: 'var(--primary, #2563eb)',
                  cursor: 'pointer',
                }}
                aria-label="Atur perbesaran foto"
              />

              <button
                type="button"
                className="button button-secondary"
                onClick={() => setZoom(z => Math.min(3.0, Number((z + 0.1).toFixed(2))))}
                style={{ minHeight: '34px', padding: '0 8px' }}
                aria-label="Zoom In"
              >
                <Plus size={14} />
              </button>

              <span
                style={{
                  fontSize: '12px',
                  fontFamily: 'monospace',
                  color: 'var(--foreground)',
                  width: '42px',
                  textAlign: 'right',
                  fontWeight: 600,
                }}
              >
                {Math.round(zoom * 100)}%
              </span>
            </div>

            {/* Utility Buttons: Fit to Frame, Rotate, Reset, and Main Action */}
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: '8px',
              }}
            >
              <div style={{ display: 'flex', gap: '6px' }}>
                <Button variant="secondary" onClick={handleFit} style={{ minHeight: '36px', padding: '0 10px', fontSize: '12px' }}>
                  <Maximize2 size={13} />
                  Pas Bingkai
                </Button>
                <Button variant="secondary" onClick={handleRotate} style={{ minHeight: '36px', padding: '0 10px', fontSize: '12px' }}>
                  <RotateCw size={13} />
                  Putar
                </Button>
                <Button variant="ghost" onClick={handleReset} style={{ minHeight: '36px', padding: '0 10px', fontSize: '12px' }}>
                  <RefreshCw size={13} />
                  Reset
                </Button>
              </div>

              {/* Action Buttons */}
              <div style={{ display: 'flex', gap: '8px' }}>
                <Button variant="secondary" onClick={() => onOpenChange(false)} style={{ minHeight: '36px', padding: '0 14px' }}>
                  Batal
                </Button>
                <Button onClick={handleCropAndApply} style={{ minHeight: '36px', padding: '0 16px' }}>
                  <Camera size={15} />
                  Gunakan Foto KTP
                </Button>
              </div>
            </div>
          </div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
