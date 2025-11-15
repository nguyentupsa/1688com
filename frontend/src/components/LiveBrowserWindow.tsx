import { useRef } from 'react';

export default function LiveBrowserWindow({ title = "Live 1688 Session" }) {
  const iframeRef = useRef<HTMLIFrameElement | null>(null);
  // ✅ dùng proxy same-origin: WS sẽ là ws(s)://host/novnc/websockify
  const src = `/vnc/vnc.html?autoconnect=1&reconnect=true&resize=scale`;

  const reload = () => {
    if (iframeRef.current) {
      const u = new URL(src, window.location.origin);
      u.searchParams.set('t', Date.now().toString()); // cache-bust
      iframeRef.current.src = u.pathname + u.search;
    }
  };

  const fullscreen = () => {
    const el = iframeRef.current;
    if (el?.requestFullscreen) el.requestFullscreen();
  };

  return (
    <div style={{
      border: '1px solid #e5e7eb',
      borderRadius: 12,
      overflow: 'hidden',
      boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
      background: '#fff'
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        padding: '8px 12px',
        borderBottom: '1px solid #f1f5f9',
        gap: 8
      }}>
        <div style={{ fontWeight: 600 }}>{title}</div>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
          <button onClick={reload}
            style={{ padding:'6px 10px', border:'1px solid #e5e7eb', borderRadius:8, background:'#fafafa', cursor:'pointer' }}>
            Reload
          </button>
          <button onClick={fullscreen}
            style={{ padding:'6px 10px', border:'1px solid #e5e7eb', borderRadius:8, background:'#fafafa', cursor:'pointer' }}>
            Fullscreen
          </button>
        </div>
      </div>

      <div style={{ height: '70vh' }}>
        <iframe
          ref={iframeRef}
          title="Live Browser (noVNC)"
          src={src}
          style={{ width:'100%', height:'100%', border:0, display:'block' }}
          // ✅ cần cho noVNC chạy JS + same-origin
          sandbox="allow-same-origin allow-scripts allow-forms allow-pointer-lock"
          // (khuyên) bật clipboard + fullscreen
          allow="clipboard-read; clipboard-write; fullscreen"
        />
      </div>
    </div>
  );
}
