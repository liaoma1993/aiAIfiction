import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { Button, Drawer, Empty, Spin, Tag, Typography } from 'antd';
import { BookOutlined, LeftOutlined, MenuOutlined, RightOutlined } from '@ant-design/icons';
import { chapterApi, projectApi, volumeApi } from '@/services/projectApi';
import './NovelPreviewPage.css';

const { Title, Text } = Typography;

export default function NovelPreviewPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const [project, setProject] = useState<any>(null);
  const [volumes, setVolumes] = useState<any[]>([]);
  const [chapters, setChapters] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [currentChapterId, setCurrentChapterId] = useState<string>('');
  const [directoryOpen, setDirectoryOpen] = useState(false);
  const readerArticleRef = useRef<HTMLElement | null>(null);
  const readerPanelRef = useRef<HTMLElement | null>(null);

  const loadData = async () => {
    if (!projectId) return;
    setLoading(true);
    try {
      const [p, v, c] = await Promise.all([
        projectApi.get(projectId),
        volumeApi.list(projectId),
        chapterApi.list(projectId),
      ]);
      setProject(p);
      setVolumes(v || []);
      setChapters(c || []);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, [projectId]);

  const directoryGroups = useMemo(() => {
    const volumeOrder = [...volumes].sort((a, b) => (a.volume_number || 0) - (b.volume_number || 0));
    const groups = volumeOrder.map((vol) => ({
      volume: vol,
      chapters: chapters
        .filter((ch: any) => ch.volume_id === vol.id)
        .sort((a: any, b: any) => (a.chapter_number || 0) - (b.chapter_number || 0)),
    }));
    const volumeIds = new Set(volumeOrder.map((vol) => vol.id));
    const unassigned = chapters
      .filter((ch: any) => !ch.volume_id || !volumeIds.has(ch.volume_id))
      .sort((a: any, b: any) => (a.chapter_number || 0) - (b.chapter_number || 0));
    if (unassigned.length) {
      groups.push({
        volume: { id: '__unassigned__', volume_number: '', title: '未分卷章节', subtitle: '', summary: '' },
        chapters: unassigned,
      });
    }
    return groups;
  }, [volumes, chapters]);

  const orderedChapters = useMemo(
    () => directoryGroups.flatMap((group) => group.chapters.map((ch: any) => ({ ...ch, volume: group.volume }))),
    [directoryGroups],
  );

  useEffect(() => {
    if (!orderedChapters.length) {
      setCurrentChapterId('');
      return;
    }
    if (!currentChapterId || !orderedChapters.some((ch) => ch.id === currentChapterId)) {
      const firstWritten = orderedChapters.find((ch) => ch.content) || orderedChapters[0];
      setCurrentChapterId(firstWritten?.id || '');
    }
  }, [orderedChapters, currentChapterId]);

  const currentIndex = useMemo(
    () => orderedChapters.findIndex((ch) => ch.id === currentChapterId),
    [orderedChapters, currentChapterId],
  );
  const currentChapter = currentIndex >= 0 ? orderedChapters[currentIndex] : null;
  const prevChapter = currentIndex > 0 ? orderedChapters[currentIndex - 1] : null;
  const nextChapter = currentIndex >= 0 && currentIndex < orderedChapters.length - 1 ? orderedChapters[currentIndex + 1] : null;

  const selectChapter = (chapterId: string) => {
    setCurrentChapterId(chapterId);
    setDirectoryOpen(false);
  };

  useEffect(() => {
    const resetScroll = () => {
      readerArticleRef.current?.scrollTo({ top: 0, left: 0, behavior: 'auto' });
      readerPanelRef.current?.scrollTo({ top: 0, left: 0, behavior: 'auto' });
      document.documentElement.scrollTo({ top: 0, left: 0, behavior: 'auto' });
      document.body.scrollTo({ top: 0, left: 0, behavior: 'auto' });
      window.scrollTo({ top: 0, left: 0, behavior: 'auto' });
    };
    resetScroll();
    const firstFrame = window.requestAnimationFrame(() => {
      resetScroll();
      window.requestAnimationFrame(resetScroll);
    });
    return () => window.cancelAnimationFrame(firstFrame);
  }, [currentChapterId]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      const tagName = target?.tagName?.toLowerCase();
      const isTyping = target?.isContentEditable || tagName === 'input' || tagName === 'textarea' || tagName === 'select';
      if (isTyping || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
      if (event.key === 'ArrowLeft' && prevChapter) {
        event.preventDefault();
        selectChapter(prevChapter.id);
      }
      if (event.key === 'ArrowRight' && nextChapter) {
        event.preventDefault();
        selectChapter(nextChapter.id);
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [prevChapter?.id, nextChapter?.id]);

  const currentVolume = currentChapter?.volume;
  const chapterCount = chapters.length;
  const writtenCount = chapters.filter((ch) => ch.content).length;
  const totalWords = chapters.reduce((sum, ch) => sum + (ch.word_count || (ch.content || '').length || 0), 0);
  const contentParagraphs = String(currentChapter?.content || '')
    .replace(/\r\n/g, '\n')
    .split(/\n{2,}/)
    .map((part) => part.trim())
    .filter(Boolean);

  if (loading) {
    return (
      <div className="novel-preview loading">
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div className="novel-preview">
      <header className="novel-preview-header">
        <div className="preview-header-left">
          <Link to={`/projects/${projectId}`} className="preview-back">
            <LeftOutlined />
            <span>返回工作台</span>
          </Link>
          <div className="preview-titleblock">
            <Title level={4} style={{ margin: 0 }}>{project?.title || '小说预览'}</Title>
            <div className="preview-subtitle">
              <Tag color="blue">{project?.genre || '未设置题材'}</Tag>
              <Tag>{volumes.length} 卷</Tag>
              <Tag>{chapterCount} 章 · 已写 {writtenCount} 章 · {totalWords} 字</Tag>
            </div>
          </div>
        </div>
        <div className="preview-header-actions">
          <Button className="preview-mobile-menu" icon={<MenuOutlined />} onClick={() => setDirectoryOpen(true)}>
            目录
          </Button>
          <Button icon={<BookOutlined />} onClick={() => navigate(`/projects/${projectId}`)}>
            去工作台
          </Button>
        </div>
      </header>

      <div className="novel-preview-body">
        <aside className="preview-directory">
          <div className="directory-head">
            <Text strong>目录</Text>
            <Text type="secondary">{chapterCount} 章</Text>
          </div>
          <div className="directory-scroll">
            {directoryGroups.length === 0 ? (
              <Empty description="暂无章节" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            ) : (
              directoryGroups
                .map(({ volume: vol, chapters: volChapters }) => {
                  return (
                    <section key={vol.id} className="directory-volume">
                      <div className="directory-volume-head">
                        <div>
                          <div className="directory-volume-title">卷{vol.volume_number} · {vol.title || '未命名卷'}</div>
                          <div className="directory-volume-subtitle">
                            {vol.subtitle || vol.summary || '暂无卷简介'}
                          </div>
                        </div>
                      </div>
                      <div className="directory-chapters">
                        {volChapters.map((ch) => (
                          <button
                            key={ch.id}
                            type="button"
                            className={`directory-chapter ${currentChapterId === ch.id ? 'active' : ''}`}
                            onClick={() => selectChapter(ch.id)}
                          >
                            <span className="chapter-index">第{ch.chapter_number}章</span>
                            <span className="chapter-title">{ch.title || '未命名章节'}</span>
                            <span className={`chapter-state ${ch.content ? 'written' : 'empty'}`}>
                              {ch.content ? `${Math.round((ch.word_count || ch.content.length || 0))}字` : '未写'}
                            </span>
                          </button>
                        ))}
                      </div>
                    </section>
                  );
                })
            )}
          </div>
        </aside>

        <main className="preview-reader" ref={readerPanelRef}>
          {currentChapter ? (
            <>
              <div className="reader-topbar">
                <div className="reader-meta">
                  <Tag color="green">卷{currentVolume?.volume_number || '--'}</Tag>
                  <Tag>{currentChapter.chapter_number} 章</Tag>
                </div>
                <div className="reader-nav">
                  <Button
                    icon={<LeftOutlined />}
                    disabled={!prevChapter}
                    onClick={() => prevChapter && selectChapter(prevChapter.id)}
                  >
                    上一章
                  </Button>
                  <Button
                    type="primary"
                    icon={<RightOutlined />}
                    disabled={!nextChapter}
                    onClick={() => nextChapter && selectChapter(nextChapter.id)}
                  >
                    下一章
                  </Button>
                </div>
              </div>

              <article key={currentChapter.id} className="reader-article" ref={readerArticleRef}>
                <div className="reader-heading">
                  <div className="reader-chapter-label">
                    第{currentChapter.chapter_number}章
                  </div>
                  <Title level={2} style={{ margin: 0 }}>
                    {currentChapter.title || '未命名章节'}
                  </Title>
                  {currentChapter.summary ? (
                    <details className="reader-blueprint">
                      <summary>章节蓝图</summary>
                      <div>{currentChapter.summary}</div>
                    </details>
                  ) : (
                    <div className="reader-submeta">暂无章节摘要</div>
                  )}
                </div>

                <div className="reader-content">
                  {currentChapter.content ? (
                    <div className="reader-text">
                      {contentParagraphs.map((paragraph, index) => (
                        <p key={index}>{paragraph}</p>
                      ))}
                    </div>
                  ) : (
                    <Empty description="本章暂无正文，切换到有内容的章节即可阅读" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                  )}
                </div>
              </article>

              <div className="reader-footer">
                <Button
                  icon={<LeftOutlined />}
                  disabled={!prevChapter}
                  onClick={() => prevChapter && selectChapter(prevChapter.id)}
                >
                  上一章
                </Button>
                <Text type="secondary">
                  {currentIndex + 1} / {orderedChapters.length}
                </Text>
                <Button
                  type="primary"
                  icon={<RightOutlined />}
                  disabled={!nextChapter}
                  onClick={() => nextChapter && selectChapter(nextChapter.id)}
                >
                  下一章
                </Button>
              </div>
            </>
          ) : (
            <div className="reader-empty">
              <Empty description="还没有可预览的章节" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            </div>
          )}
        </main>
      </div>

      <Drawer
        title="目录"
        open={directoryOpen}
        onClose={() => setDirectoryOpen(false)}
        width={320}
        bodyStyle={{ padding: 0 }}
      >
        <div className="drawer-directory">
          {directoryGroups
            .map(({ volume: vol, chapters: volChapters }) => {
              return (
                <div key={vol.id} className="drawer-volume">
                  <div className="drawer-volume-title">卷{vol.volume_number} · {vol.title || '未命名卷'}</div>
                  <div className="drawer-volume-chapters">
                    {volChapters.map((ch) => (
                      <button
                        key={ch.id}
                        type="button"
                        className={`drawer-chapter ${currentChapterId === ch.id ? 'active' : ''}`}
                        onClick={() => selectChapter(ch.id)}
                      >
                        第{ch.chapter_number}章 · {ch.title || '未命名章节'}
                      </button>
                    ))}
                  </div>
                </div>
              );
            })}
        </div>
      </Drawer>
    </div>
  );
}
