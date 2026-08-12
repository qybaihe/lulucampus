import { useCallback, useEffect, useRef, useState } from "react";
import type {
  TasteProfileResult,
  TasteSourceProfile,
} from "../../core/api/repositories";
import { LuluSprite } from "../../components/lulu/LuluSprite";
import { Btn } from "../../components/ui/primitives";
import { PersonaCard } from "./PersonaCard";
import { exportNodePng } from "./exportCard";
import {
  analyzeFromShareLink,
  fetchDemoStatus,
  type DemoTasteStatus,
} from "./demoTasteApi";

type Phase =
  | { kind: "boot" }
  | { kind: "generating" }
  | { kind: "ready" }
  | { kind: "failed"; message: string };

function errMessage(err: unknown): string {
  return err instanceof Error ? err.message : String(err);
}

/**
 * 公开体验页：粘贴抖音主页分享链接 → 生成画像 → 导出分享卡。
 */
export function DemoTasteScreen() {
  const [phase, setPhase] = useState<Phase>({ kind: "boot" });
  const [statusInfo, setStatusInfo] = useState<DemoTasteStatus | null>(null);
  const [result, setResult] = useState<TasteProfileResult | null>(null);
  const [profile, setProfile] = useState<TasteSourceProfile | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [shareText, setShareText] = useState("");
  const [linkBusy, setLinkBusy] = useState(false);
  const [exporting, setExporting] = useState(false);
  const cardRef = useRef<HTMLDivElement | null>(null);
  const goneRef = useRef(false);

  const showToast = useCallback((text: string) => {
    setToast(text);
    window.setTimeout(() => setToast((cur) => (cur === text ? null : cur)), 2400);
  }, []);

  useEffect(() => {
    goneRef.current = false;
    void (async () => {
      try {
        const info = await fetchDemoStatus();
        if (goneRef.current) return;
        setStatusInfo(info);
        if (!info.enabled) {
          setPhase({
            kind: "failed",
            message: info.message || "体验入口未开启",
          });
        }
      } catch (err) {
        if (!goneRef.current) {
          setPhase({ kind: "failed", message: errMessage(err) });
        }
      }
    })();
    return () => {
      goneRef.current = true;
    };
  }, []);

  const onAnalyzeLink = async () => {
    const text = shareText.trim();
    if (!text || linkBusy) return;
    setLinkBusy(true);
    setPhase({ kind: "generating" });
    try {
      const data = await analyzeFromShareLink(text);
      if (goneRef.current) return;
      setProfile(data.source_profile ?? null);
      setResult(data.result);
      setPhase({ kind: "ready" });
    } catch (err) {
      if (!goneRef.current) {
        setPhase({ kind: "failed", message: errMessage(err) });
      }
    } finally {
      setLinkBusy(false);
    }
  };

  const onRestart = () => {
    setResult(null);
    setProfile(null);
    setShareText("");
    setPhase({ kind: "boot" });
  };

  const onExportCard = async () => {
    const node = cardRef.current;
    if (!node || exporting) return;
    setExporting(true);
    try {
      const dataUrl = await exportNodePng(node);
      const nick = profile?.nickname?.trim() || "douyin";
      const safe = nick.replace(/[^\w\u4e00-\u9fff-]+/g, "_").slice(0, 32);
      const a = document.createElement("a");
      a.href = dataUrl;
      a.download = `噜噜抖音画像_${safe}.png`;
      a.click();
      showToast("画像卡片已导出");
    } catch (err) {
      showToast(errMessage(err) || "导出失败，请重试");
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="demo-taste-page" data-od-id="demo-taste">
      <div className="demo-taste-shell">
        <header className="demo-taste-hero">
          <h1 className="demo-taste-title">让噜噜看看你的抖音画像</h1>
          <p className="demo-taste-lead">
            把抖音个人主页的分享链接贴过来。噜噜会一起看你最近的喜欢和收藏，生成一张可分享的兴趣画像卡。
          </p>
        </header>

        <main className="demo-taste-card">
          {phase.kind === "boot" ? (
            <div className="taste-stage" style={{ alignItems: "stretch" }}>
              <div className="center">
                <LuluSprite clip="home.listening" size={120} />
              </div>
              <div className="t-t2 center mt-2">粘贴主页分享链接</div>
              <ol className="share-howto">
                <li>打开抖音，点底部「我」</li>
                <li>点自己的抖音号，进入抖音码页面</li>
                <li>点右上角分享箭头，再选「复制链接」</li>
                <li>打开「设置 → 隐私与政策 → 收藏」，把里面的「视频」设为公开</li>
                <li>把主页「喜欢」也设为公开，然后粘贴到下面</li>
              </ol>
              <textarea
                className="om-input mt-3"
                rows={4}
                value={shareText}
                onChange={(e) => setShareText(e.target.value)}
                placeholder="粘贴整段分享卡片也可以，例如：长按复制此条消息… https://v.douyin.com/xxxx/"
                data-od-id="demo-taste-share-input"
              />
              <div className="mt-3">
                <Btn
                  kind="primary"
                  disabled={linkBusy || shareText.trim().length < 8}
                  onClick={() => void onAnalyzeLink()}
                >
                  {linkBusy ? "分析中…" : "让噜噜看看"}
                </Btn>
              </div>
              {statusInfo?.http_link_import_ready === false ? (
                <div className="t-foot mt-3 center">服务暂未就绪，请稍后再试。</div>
              ) : null}
            </div>
          ) : null}

          {phase.kind === "generating" ? (
            <div className="taste-stage">
              <LuluSprite clip="home.thinking" size={150} />
              <div className="t-t2 mt-3">噜噜正在看你的喜欢和收藏</div>
              <div className="t-foot mt-1">马上就好，请稍等一会儿。</div>
            </div>
          ) : null}

          {phase.kind === "ready" && result ? (
            <>
              <PersonaCard
                ref={cardRef}
                result={result}
                profile={profile}
                variant="share"
              />
              <div className="demo-taste-actions">
                <Btn
                  kind="primary"
                  disabled={exporting}
                  onClick={() => void onExportCard()}
                >
                  {exporting ? "导出中…" : "导出画像卡片"}
                </Btn>
                <Btn kind="ghost" onClick={onRestart}>
                  再看一个
                </Btn>
              </div>
            </>
          ) : null}

          {phase.kind === "failed" ? (
            <div className="taste-stage">
              <LuluSprite clip="core.care" size={140} />
              <div className="t-t2 mt-3">这次没成功</div>
              <div className="t-foot mt-1 center" style={{ maxWidth: 300 }}>
                {phase.message}
              </div>
              <div className="mt-5" style={{ width: "100%" }}>
                <Btn kind="primary" onClick={onRestart}>
                  重新开始
                </Btn>
              </div>
            </div>
          ) : null}
        </main>
      </div>
      <div className={`om-toast ${toast ? "show" : ""}`}>{toast}</div>
    </div>
  );
}
