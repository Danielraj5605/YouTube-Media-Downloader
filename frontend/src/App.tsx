import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import {
  Search,
  Download,
  Loader2,
  CheckCircle2,
  AlertCircle,
  PlayCircle,
  ChevronDown,
  Sun,
  Moon,
  ListMusic,
  Package,
} from 'lucide-react';

const API_BASE_URL = 'http://localhost:8000';

interface VideoFormat {
  format_id: string;
  resolution: string;
  ext: string;
  filesize?: number;
  note?: string;
}

interface PlaylistVideo {
  title: string;
  duration?: number;
  thumbnail?: string;
  url: string;
}

interface VideoInfo {
  is_playlist: boolean;
  title: string;
  thumbnail: string;
  duration: number;
  uploader: string;
  formats: VideoFormat[];
  url: string;
  video_count?: number;
  videos?: PlaylistVideo[];
}

interface ProgressData {
  status: string;
  progress: number;
  speed: string;
  eta: string;
  filename: string | null;
  completed: boolean;
  error: string | null;
  // Playlist fields
  is_playlist?: boolean;
  total_videos?: number;
  current_video?: number;
  current_video_title?: string;
}

function App() {
  // ─── Theme ───
  const [dark, setDark] = useState(() => {
    const stored = localStorage.getItem('sg-theme');
    if (stored) return stored === 'dark';
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  });

  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark);
    localStorage.setItem('sg-theme', dark ? 'dark' : 'light');
  }, [dark]);

  // ─── App state ───
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [videoInfo, setVideoInfo] = useState<VideoInfo | null>(null);
  const [selectedFormat, setSelectedFormat] = useState('');
  const [downloading, setDownloading] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [progress, setProgress] = useState<ProgressData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const analyzeUrl = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url) return;

    setLoading(true);
    setError(null);
    setVideoInfo(null);
    setTaskId(null);
    setProgress(null);

    try {
      const response = await axios.post(`${API_BASE_URL}/api/analyze`, { url });
      setVideoInfo(response.data);
      if (response.data.formats.length > 0) {
        setSelectedFormat(response.data.formats[0].format_id);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to analyze URL. Please check if it is a valid YouTube link.');
    } finally {
      setLoading(false);
    }
  };

  const startDownload = async () => {
    if (!videoInfo || !selectedFormat) return;

    setDownloading(true);
    setError(null);
    setProgress(null);

    try {
      let response;
      if (videoInfo.is_playlist && videoInfo.videos && videoInfo.videos.length > 0) {
        // Playlist download
        response = await axios.post(`${API_BASE_URL}/api/download-playlist`, {
          url: videoInfo.url,
          format_id: selectedFormat,
          videos: videoInfo.videos.map((v) => ({ title: v.title, url: v.url })),
        });
      } else {
        // Single video download
        response = await axios.post(`${API_BASE_URL}/api/download`, {
          url: videoInfo.url,
          format_id: selectedFormat,
        });
      }
      setTaskId(response.data.task_id);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to start download.');
      setDownloading(false);
    }
  };

  // Poll for progress when taskId is set
  useEffect(() => {
    if (!taskId) return;

    const poll = async () => {
      try {
        const res = await axios.get(`${API_BASE_URL}/api/progress/${taskId}`);
        const data: ProgressData = res.data;
        setProgress(data);

        if (data.completed || data.error) {
          if (pollingRef.current) {
            clearInterval(pollingRef.current);
            pollingRef.current = null;
          }
          setDownloading(false);
        }
      } catch {
        if (pollingRef.current) {
          clearInterval(pollingRef.current);
          pollingRef.current = null;
        }
        setDownloading(false);
      }
    };

    poll();
    pollingRef.current = setInterval(poll, 1000);

    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [taskId]);

  const fetchFile = () => {
    if (!taskId) return;
    window.location.href = `${API_BASE_URL}/api/fetch/${taskId}`;
  };

  const resetAll = () => {
    setVideoInfo(null);
    setTaskId(null);
    setProgress(null);
    setDownloading(false);
    setUrl('');
    setError(null);
  };

  const formatDuration = (seconds: number) => {
    if (!seconds) return '0:00';
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    if (hrs > 0) {
      return `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const formatSize = (bytes?: number) => {
    if (!bytes) return 'N/A';
    const mb = bytes / (1024 * 1024);
    if (mb > 1024) return `${(mb / 1024).toFixed(1)} GB`;
    return `${mb.toFixed(1)} MB`;
  };

  // Compute overall progress for playlists
  const getOverallProgress = () => {
    if (!progress) return 0;
    if (!progress.is_playlist) return progress.progress;
    const total = progress.total_videos || 1;
    const done = (progress.current_video || 1) - 1; // videos fully done
    const currentPct = progress.progress || 0;
    return ((done + currentPct / 100) / total) * 100;
  };

  return (
    <div className="min-h-screen font-sans">
      {/* Navbar */}
      <nav className="border-b border-[var(--border)] py-4 px-6 sticky top-0 bg-[var(--bg)]/80 backdrop-blur-md z-50">
        <div className="max-w-6xl mx-auto flex justify-between items-center">
          <div className="flex items-center gap-2">
            <div className="w-10 h-10 bg-[var(--accent)] rounded-xl flex items-center justify-center text-white shadow-lg shadow-[var(--accent)]/30">
              <Download size={24} />
            </div>
            <span className="text-2xl font-bold tracking-tight text-[var(--text-h)]">StreamGrab</span>
          </div>
          <div className="flex items-center gap-4">
            <button
              onClick={() => setDark((d) => !d)}
              className="w-10 h-10 rounded-xl flex items-center justify-center border border-[var(--border)] bg-[var(--code-bg)] hover:border-[var(--accent)] transition-all cursor-pointer"
              aria-label="Toggle theme"
            >
              {dark ? <Sun size={18} className="text-amber-400" /> : <Moon size={18} className="text-[var(--text)]" />}
            </button>
          </div>
        </div>
      </nav>

      <main className="max-w-4xl mx-auto px-6 py-12">
        {/* Hero Section */}
        <section className="text-center mb-12 animate-in fade-in slide-in-from-bottom-4 duration-700">
          <h1 className="text-5xl md:text-6xl font-bold mb-6 tracking-tight">
            Download your favorite <span className="text-[var(--accent)]">YouTube</span> content
          </h1>
          <p className="text-xl text-[var(--text)] max-w-2xl mx-auto">
            Fast, high-quality video and audio downloads. No limits, no ads, just smooth grabbing.
          </p>
        </section>

        {/* URL Input Box */}
        <section className="mb-12">
          <form onSubmit={analyzeUrl} className="relative group">
            <div className="absolute inset-0 bg-[var(--accent)]/10 blur-xl group-hover:bg-[var(--accent)]/20 transition-all duration-500 rounded-2xl"></div>
            <div className="relative flex flex-col md:flex-row gap-3 p-2 bg-[var(--bg)] border-2 border-[var(--border)] rounded-2xl focus-within:border-[var(--accent)] transition-all duration-300 shadow-xl shadow-black/5">
              <div className="flex-1 flex items-center px-4">
                <Search className="text-[var(--text)] mr-3 shrink-0" size={20} />
                <input
                  type="text"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="Paste YouTube video or playlist URL here..."
                  className="w-full bg-transparent border-none outline-none py-4 text-lg text-[var(--text-h)] placeholder:text-[var(--text)]/50"
                />
              </div>
              <button
                type="submit"
                disabled={loading || !url}
                className="bg-[var(--accent)] hover:brightness-110 disabled:opacity-50 disabled:hover:brightness-100 text-white font-semibold py-4 px-8 rounded-xl transition-all flex items-center justify-center gap-2 cursor-pointer"
              >
                {loading ? <Loader2 className="animate-spin" size={20} /> : <Search size={20} />}
                {loading ? 'Analyzing...' : 'Analyze'}
              </button>
            </div>
          </form>
          {error && (
            <div className="mt-4 p-4 bg-red-500/10 border border-red-500/50 rounded-xl flex items-center gap-3 text-red-500 animate-in fade-in slide-in-from-top-2">
              <AlertCircle size={20} />
              <span>{error}</span>
            </div>
          )}
        </section>

        {/* Results / Progress Area */}
        <section className="space-y-8">
          {/* ─── Video / Playlist Info Card ─── */}
          {videoInfo && !progress && (
            <div className="bg-[var(--bg)] border border-[var(--border)] rounded-3xl overflow-hidden shadow-2xl animate-in fade-in zoom-in-95 duration-500">
              <div className="flex flex-col md:flex-row">
                <div className="md:w-2/5 relative aspect-video md:aspect-auto">
                  <img src={videoInfo.thumbnail} alt={videoInfo.title} className="w-full h-full object-cover" />
                  {videoInfo.duration > 0 && (
                    <div className="absolute bottom-4 right-4 bg-black/70 backdrop-blur-md text-white text-xs font-mono px-2 py-1 rounded">
                      {formatDuration(videoInfo.duration)}
                    </div>
                  )}
                  {videoInfo.is_playlist && (
                    <div className="absolute top-4 left-4 bg-[var(--accent)] text-white text-xs font-bold px-3 py-1 rounded-full flex items-center gap-1.5">
                      <ListMusic size={12} />
                      Playlist · {videoInfo.video_count} videos
                    </div>
                  )}
                  <div className="absolute inset-0 flex items-center justify-center opacity-0 hover:opacity-100 transition-opacity bg-black/20">
                    <PlayCircle size={64} className="text-white drop-shadow-lg" />
                  </div>
                </div>
                <div className="md:w-3/5 p-8 flex flex-col justify-between">
                  <div>
                    <h2 className="text-2xl font-bold mb-2 line-clamp-2">{videoInfo.title}</h2>
                    <p className="text-[var(--text)] flex items-center gap-1 mb-4">
                      By {videoInfo.uploader}
                    </p>

                    {/* Playlist video list */}
                    {videoInfo.is_playlist && videoInfo.videos && videoInfo.videos.length > 0 && (
                      <div className="mb-4 max-h-48 overflow-y-auto rounded-xl border border-[var(--border)] bg-[var(--code-bg)]">
                        {videoInfo.videos.slice(0, 50).map((v, i) => (
                          <div key={i} className="flex items-center gap-3 px-4 py-2.5 border-b border-[var(--border)] last:border-b-0 hover:bg-[var(--bg)] transition-colors">
                            <span className="text-xs font-mono text-[var(--text)] w-6 text-right shrink-0">{i + 1}</span>
                            {v.thumbnail && (
                              <img src={v.thumbnail} alt="" className="w-12 h-7 rounded object-cover shrink-0" />
                            )}
                            <span className="text-sm text-[var(--text-h)] truncate flex-1">{v.title}</span>
                            {v.duration ? (
                              <span className="text-xs font-mono text-[var(--text)] shrink-0">{formatDuration(v.duration)}</span>
                            ) : null}
                          </div>
                        ))}
                        {videoInfo.videos.length > 50 && (
                          <div className="px-4 py-2 text-xs text-[var(--text)] text-center">
                            +{videoInfo.videos.length - 50} more videos
                          </div>
                        )}
                      </div>
                    )}

                    <div className="space-y-4 mb-6">
                      <div className="relative">
                        <label className="text-xs font-bold uppercase tracking-wider text-[var(--text)] mb-2 block">Select Quality</label>
                        <div className="relative group">
                          <select
                            value={selectedFormat}
                            onChange={(e) => setSelectedFormat(e.target.value)}
                            className="w-full bg-[var(--code-bg)] border border-[var(--border)] rounded-xl py-3 px-4 appearance-none cursor-pointer focus:border-[var(--accent)] outline-none transition-colors text-[var(--text-h)]"
                          >
                            {videoInfo.formats.map((f) => (
                              <option key={f.format_id} value={f.format_id}>
                                {f.resolution} {f.ext} {f.note ? `(${f.note})` : ''} — {formatSize(f.filesize)}
                              </option>
                            ))}
                          </select>
                          <ChevronDown className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none text-[var(--text)]" size={20} />
                        </div>
                      </div>
                    </div>
                  </div>

                  <button
                    onClick={startDownload}
                    disabled={downloading}
                    className="w-full bg-[var(--text-h)] text-[var(--bg)] py-4 rounded-xl font-bold flex items-center justify-center gap-2 hover:opacity-90 transition-all disabled:opacity-50 cursor-pointer"
                  >
                    {downloading ? <Loader2 className="animate-spin" size={24} /> : <Download size={24} />}
                    {downloading
                      ? 'Preparing...'
                      : videoInfo.is_playlist
                      ? `Download All ${videoInfo.video_count} Videos`
                      : 'Start Download'}
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* ─── Download Progress Card ─── */}
          {progress && (
            <div className="rounded-3xl overflow-hidden shadow-2xl animate-in fade-in slide-in-from-bottom-8 border border-white/10 relative" style={{ background: '#0d0d14' }}>
              {/* Blurred thumbnail background */}
              {videoInfo?.thumbnail && (
                <div className="absolute inset-0 z-0">
                  <img
                    src={videoInfo.thumbnail}
                    alt=""
                    className="w-full h-full object-cover scale-110"
                    style={{ filter: 'blur(32px) brightness(0.25) saturate(1.8)' }}
                  />
                  <div className="absolute inset-0" style={{ background: 'linear-gradient(135deg, rgba(13,13,20,0.85) 0%, rgba(13,13,20,0.7) 100%)' }} />
                </div>
              )}

              <div className="relative z-10 p-8">
                {/* Header row */}
                <div className="flex items-start gap-5 mb-7">
                  {videoInfo?.thumbnail && (
                    <div className="shrink-0 w-20 h-14 rounded-xl overflow-hidden border border-white/10 shadow-lg shadow-black/40">
                      <img src={videoInfo.thumbnail} alt="" className="w-full h-full object-cover" />
                    </div>
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-semibold uppercase tracking-widest mb-1" style={{ color: '#c084fc', letterSpacing: '0.12em' }}>
                      {progress.completed
                        ? '✓  Complete'
                        : progress.error
                        ? '✗  Failed'
                        : progress.status === 'processing'
                        ? '⚙  Processing…'
                        : progress.is_playlist
                        ? `↓  Downloading ${progress.current_video || 1} of ${progress.total_videos}`
                        : '↓  Downloading'}
                    </p>
                    <h3 className="text-lg font-bold leading-snug line-clamp-2" style={{ color: '#f1f0f8' }}>
                      {progress.is_playlist && progress.current_video_title
                        ? progress.current_video_title
                        : videoInfo?.title || 'Preparing…'}
                    </h3>
                    {videoInfo?.uploader && (
                      <p className="text-xs mt-0.5" style={{ color: 'rgba(241,240,248,0.55)' }}>{videoInfo.uploader}</p>
                    )}
                  </div>
                </div>

                {/* ── In-progress state ── */}
                {!progress.completed && !progress.error && (
                  <div className="space-y-5">
                    {/* Playlist overall progress (if playlist) */}
                    {progress.is_playlist && (progress.total_videos || 0) > 1 && (
                      <div className="space-y-2">
                        <div className="flex justify-between text-xs font-semibold" style={{ color: 'rgba(241,240,248,0.6)' }}>
                          <span>Overall</span>
                          <span>{progress.current_video || 1} / {progress.total_videos} videos</span>
                        </div>
                        <div className="w-full h-1.5 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.06)' }}>
                          <div
                            className="h-full rounded-full transition-all duration-500 ease-out"
                            style={{
                              width: `${getOverallProgress()}%`,
                              background: 'linear-gradient(90deg, #6366f1, #818cf8)',
                            }}
                          />
                        </div>
                      </div>
                    )}

                    {/* Current file progress bar */}
                    <div className="relative">
                      <div className="w-full h-2.5 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.08)' }}>
                        <div
                          className="h-full rounded-full transition-all duration-500 ease-out relative"
                          style={{
                            width: `${progress.progress}%`,
                            background: 'linear-gradient(90deg, #a855f7, #c084fc, #e879f9)',
                            boxShadow: '0 0 12px 3px rgba(192, 132, 252, 0.55)',
                          }}
                        >
                          <div
                            className="absolute inset-0 rounded-full"
                            style={{
                              background: 'linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.35) 50%, transparent 100%)',
                              animation: 'shimmer 1.6s infinite',
                            }}
                          />
                        </div>
                      </div>
                    </div>

                    {/* Stats row */}
                    <div className="flex flex-wrap items-center gap-3">
                      <span
                        className="text-3xl font-extrabold tabular-nums"
                        style={{ color: '#c084fc', textShadow: '0 0 20px rgba(192,132,252,0.5)' }}
                      >
                        {progress.progress.toFixed(1)}%
                      </span>

                      <div className="flex flex-wrap gap-2 ml-auto">
                        <div
                          className="flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold"
                          style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.12)', color: '#e2e0f0' }}
                        >
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse inline-block" />
                          {progress.speed || 'Starting…'}
                        </div>
                        {progress.status !== 'processing' && (
                          <div
                            className="flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold"
                            style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.12)', color: '#e2e0f0' }}
                          >
                            <span style={{ opacity: 0.5 }}>ETA</span>
                            &nbsp;{progress.eta || '–'}
                          </div>
                        )}
                        {progress.status === 'processing' && (
                          <div
                            className="flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold"
                            style={{ background: 'rgba(192,132,252,0.15)', border: '1px solid rgba(192,132,252,0.4)', color: '#c084fc' }}
                          >
                            <Loader2 size={11} className="animate-spin" />
                            Finalizing…
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )}

                {/* ── Complete state ── */}
                {progress.completed && (
                  <div className="space-y-4">
                    <div className="flex items-center gap-3 p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/25">
                      <CheckCircle2 size={22} className="text-emerald-400 shrink-0" />
                      <span className="text-sm font-medium text-emerald-300">
                        {progress.is_playlist
                          ? `All ${progress.total_videos} videos are ready — download as ZIP.`
                          : 'Your file is ready — tap below to save it.'}
                      </span>
                    </div>
                    <div className="flex flex-col sm:flex-row gap-3">
                      <button
                        onClick={fetchFile}
                        className="flex-1 py-4 rounded-2xl font-bold flex items-center justify-center gap-2 transition-all cursor-pointer text-white"
                        style={{
                          background: 'linear-gradient(135deg, #a855f7 0%, #7c3aed 100%)',
                          boxShadow: '0 4px 24px rgba(168, 85, 247, 0.45)',
                        }}
                      >
                        {progress.is_playlist ? <Package size={20} /> : <Download size={20} />}
                        {progress.is_playlist ? 'Download ZIP' : 'Save to Device'}
                      </button>
                      <button
                        onClick={resetAll}
                        className="bg-white/5 border border-white/10 text-[var(--text-h)] px-8 py-4 rounded-2xl font-bold hover:bg-white/10 transition-all cursor-pointer"
                      >
                        New Download
                      </button>
                    </div>
                  </div>
                )}

                {/* ── Error state ── */}
                {progress.error && (
                  <div className="space-y-4">
                    <div className="p-4 bg-red-500/10 border border-red-500/25 rounded-2xl flex items-start gap-3">
                      <AlertCircle size={18} className="text-red-400 mt-0.5 shrink-0" />
                      <p className="text-red-300 text-sm leading-relaxed">{progress.error}</p>
                    </div>
                    <button
                      onClick={() => {
                        setTaskId(null);
                        setProgress(null);
                        setDownloading(false);
                      }}
                      className="w-full bg-red-500/80 hover:bg-red-500 text-white py-4 rounded-2xl font-bold cursor-pointer transition-colors"
                    >
                      Try Again
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}
        </section>
      </main>

      {/* Footer */}
      <footer className="mt-20 border-t border-[var(--border)] py-12 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <div className="flex items-center justify-center gap-2 mb-4">
            <div className="w-8 h-8 bg-[var(--text)]/10 rounded-lg flex items-center justify-center text-[var(--text)]">
              <Download size={16} />
            </div>
            <span className="font-bold text-[var(--text-h)]">StreamGrab</span>
          </div>
          <p className="text-[var(--text)] text-sm mb-6">
            The smartest way to grab YouTube media. Optimized for speed and quality.
          </p>
          <div className="flex justify-center gap-6 text-[var(--text)]">
            <a href="#" className="hover:text-[var(--accent)] transition-colors">Privacy</a>
            <a href="#" className="hover:text-[var(--accent)] transition-colors">Terms</a>
            <a href="#" className="hover:text-[var(--accent)] transition-colors">Contact</a>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
