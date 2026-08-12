import { useEffect, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { LuluSprite } from "../../components/lulu/LuluSprite";
import { assetURL } from "../../core/assets";

/**
 * 营销首页（Landing）。全宽文档流，不进 PhoneFrame。
 * 文案事实来源：docs/00_产品方案_V2.1.md 与 README 产品红线。
 */

const APP_ICON = assetURL("/assets/landing/app-icon.png");

function CheckIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 15 15" aria-hidden>
      <circle cx="7.5" cy="7.5" r="7" fill="var(--yolk)" />
      <path
        d="M4.4 7.7l2 2 4-4.4"
        stroke="var(--ink)"
        strokeWidth="1.6"
        fill="none"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function HeroChip({
  className,
  sticker,
  label,
  need,
}: {
  className: string;
  sticker: string;
  label: string;
  need: number;
}) {
  return (
    <div className={`lp-chip ${className}`} aria-hidden>
      <img src={assetURL(`/assets/stickers/${sticker}.png`)} alt="" loading="lazy" />
      <div>
        {label}
        <span className="need">
          还差<b>{need}</b>
        </span>
      </div>
    </div>
  );
}

/** 前情提要：SYSU Anything 已打通的校园系统（与小红书帖子口径一致）。 */
const CONNECTED_SYSTEMS: ReadonlyArray<{ sticker: string; name: string }> = [
  { sticker: "teaching-building", name: "教务系统" },
  { sticker: "access-card", name: "学工系统" },
  { sticker: "algorithm-gear", name: "交叉探索" },
  { sticker: "notebook-open", name: "雨课堂" },
  { sticker: "envelope", name: "就业信息" },
  { sticker: "school-bus", name: "岐关车" },
  { sticker: "badminton", name: "体育馆预订" },
];

const FAQS: ReadonlyArray<{ q: string; a: ReactNode }> = [
  {
    q: "噜噜成局是什么？",
    a: (
      <p>
        一句话：帮你把「差一个人」的局补齐的校园智能体。它不是社交软件——没有信息流、
        不推荐好友。你有明确想做的事（打球、自习、组队、拼车），噜噜负责把人凑齐、
        把研讨室或场馆预约办好，然后退场。
      </p>
    ),
  },
  {
    q: "和小红书上的 SYSU Anything 是什么关系？",
    a: (
      <p>
        SYSU Anything 是我们先做出来的校园接入技能——就是那篇《我把中大的校园系统，
        接进 agent 了》里的主角。噜噜成局把它作为底层执行器：那些已经打通的校园系统，
        现在直接支撑「今天」Tab 的查询与预约能力，再往上叠加成局撮合和信任体系。
      </p>
    ),
  },
  {
    q: "谁可以用？",
    a: (
      <p>
        所有在校学生都可以用。我们对中山大学做了深度定制优化——三校区五校园覆盖、
        校园系统直连、学校统一身份扫码认证，开箱即是完整体验；其他学校的同学同样可以
        发起和加入局，校园系统能力会随接入逐步开放。所有用户都需完成校园身份认证，
        保证局里出现的每一个人都是真实的在校学生。
      </p>
    ),
  },
  {
    q: "发出「差一个」之后会发生什么？",
    a: (
      <p>
        噜噜先用一两轮对话跟你确认细节（做什么、何时、何地、差几个、什么角色），
        然后把意图匿名放进池子撮合。人找齐后所有人一起确认才建局；有人退出会自动补位。
        全程不需要你去加好友，也不需要私聊陌生人。
      </p>
    ),
  },
  {
    q: "我的课表和身份数据安全吗？",
    a: (
      <p>
        每一类校园数据都单独授权、随时可撤回，撤回会级联清除对应数据。空档匹配只交换
        「这个时段有没有空」，不会把课表交给任何人；系统不读取成绩，校园凭证加密存储。
        详见<Link to="/legal/privacy">《隐私政策》</Link>。
      </p>
    ),
  },
  {
    q: "有哪些客户端？",
    a: (
      <p>
        网页版即开即用，手机与电脑浏览器都支持；原生 iOS 客户端已完成开发，正在准备上架。
        两端连接同一套服务，进度实时同步。
      </p>
    ),
  },
];

export function LandingScreen() {
  useEffect(() => {
    const prev = document.title;
    document.title = "噜噜成局 — 差一个，就成局";
    return () => {
      document.title = prev;
    };
  }, []);

  return (
    <div className="lp" data-od-id="landing-root" data-screen="landing">
      <header className="lp-header">
        <div className="lp-container lp-header-inner">
          <a className="lp-brand" href="#top" aria-label="噜噜成局">
            <img src={APP_ICON} alt="" />
            噜噜成局
          </a>
          <nav className="lp-nav" aria-label="页面导航">
            <a href="#story">前情提要</a>
            <a href="#how">怎么成局</a>
            <a href="#features">能做什么</a>
            <a href="#principles">我们不做</a>
            <a href="#faq">常见问题</a>
          </nav>
          <div className="lp-header-cta">
            <Link className="lp-btn primary sm" to="/app">
              打开网页版
            </Link>
          </div>
        </div>
      </header>

      <main id="top">
        {/* ---------- Hero ---------- */}
        <section className="lp-hero">
          <div className="lp-container lp-hero-inner">
            <div>
              <span className="lp-eyebrow">
                <span className="dot" aria-hidden />
                校园成局智能体 · 面向所有学生 · 中大深度定制
              </span>
              <h1>
                <span className="gap-mark">差一个</span>，
                <br />
                就成局。
              </h1>
              <p className="lp-hero-sub">
                打球差一个、组队差一个、自习差一个——把缺的那个人交给噜噜。
                它按<strong>共同空档、校区可达、能力互补</strong>把局补齐；
                <strong>AI 不介绍人，AI 促成事</strong>，局成了就安静退场。
              </p>
              <div className="lp-hero-ctas">
                <Link className="lp-btn primary lg" to="/app" data-od-id="landing-cta-open-app">
                  打开噜噜成局
                </Link>
                <a className="lp-btn ghost lg" href="#how">
                  看看噜噜怎么工作
                </a>
              </div>
              <div className="lp-hero-meta">
                <span>
                  <CheckIcon />
                  校园实名身份
                </span>
                <span>
                  <CheckIcon />
                  匿名进池撮合
                </span>
                <span>
                  <CheckIcon />
                  全员确认才成局
                </span>
              </div>
            </div>

            <div className="lp-hero-stage" aria-label="噜噜与正在等待补齐的局">
              <div className="halo" aria-hidden />
              <div className="ring" aria-hidden />
              <LuluSprite clip="home.idle" size={300} />
              <HeroChip className="c1" sticker="basketball" label="今晚南校打球" need={1} />
              <HeroChip className="c2" sticker="trophy" label="数模国赛组队" need={2} />
              <HeroChip className="c3" sticker="books-stack" label="期末图书馆自习" need={1} />
              <HeroChip className="c4" sticker="school-bus" label="明早拼车跨校区" need={1} />
            </div>
          </div>
        </section>

        {/* ---------- 前情提要：两个先跑通的技能 ---------- */}
        <section className="lp-section" id="story">
          <div className="lp-container">
            <div className="lp-story-head">
              <div>
                <span className="lp-kicker">前情提要</span>
                <h2>
                  噜噜的本事，
                  <br />
                  从两个技能开始
                </h2>
                <p className="intro">
                  在拼成噜噜之前，我们先把两件事在真实校园里跑通：
                  一个替你跑腿校园系统，一个让 AI 读懂你的口味。
                </p>
              </div>
              <div className="lp-story-lulu" aria-hidden>
                <LuluSprite clip="home.reply" size={168} caption="先跑通，再拼进噜噜" />
              </div>
            </div>

            <div className="lp-skills">
              <article className="lp-skill">
                <span className="lp-skill-no">技能 01 · 校园系统接入</span>
                <h3>SYSU Anything</h3>
                <p className="lp-skill-sub">
                  校园助手功能的起点：把中大的校园系统一个个接进 AI 智能体——
                  查课表、盯作业、订场馆、搭班车，都变成一句话的事。它以
                  《我把中大的校园系统，接进 agent 了》在小红书上被两万多名同学看到。
                </p>
                <div className="lp-story-stats" role="list" aria-label="小红书数据">
                  <div role="listitem">
                    <b>2万+</b>
                    <span>小红书浏览</span>
                  </div>
                  <div role="listitem">
                    <b>1100+</b>
                    <span>点赞</span>
                  </div>
                  <div role="listitem">
                    <b>600+</b>
                    <span>收藏</span>
                  </div>
                  <div role="listitem">
                    <b>680+</b>
                    <span>转发</span>
                  </div>
                </div>
                <h4 className="lp-skill-h4">
                  <span className="dot" aria-hidden />
                  已打通的校园系统
                </h4>
                <ul className="lp-story-systems">
                  {CONNECTED_SYSTEMS.map((s) => (
                    <li key={s.name}>
                      <img
                        src={assetURL(`/assets/stickers/${s.sticker}.png`)}
                        alt=""
                        loading="lazy"
                      />
                      {s.name}
                    </li>
                  ))}
                </ul>
                <div className="lp-hermes-demo" aria-label="校园助手示例">
                  <span className="q">“明早二节后有空教室吗？再看看体育馆羽毛球场。”</span>
                  <span className="a">
                    查到了：东校园 D203 空闲；体育馆 19:00 有羽毛球场——要帮你预订吗？
                  </span>
                </div>
                <p className="lp-story-so">
                  这套执行器，现在就是「今天」Tab 背后的 <strong>hermes</strong>：
                  课表与空教室即问即答、作业 DDL 自动进提醒、体育馆空档直接预订、
                  跨校区班车一句话查到。
                </p>
              </article>

              <article className="lp-skill">
                <span className="lp-skill-no">技能 02 · 兴趣画像</span>
                <h3>抖音画像分析导入</h3>
                <p className="lp-skill-sub">
                  让 AI 在第一次见面前就了解你：扫一个码，把你在抖音里「喜欢」的内容，
                  变成一张讲人话的兴趣画像。
                </p>
                <ol className="lp-chain">
                  <li>
                    <span className="cnum">1</span>
                    <div>
                      <b>抖音扫码授权</b>
                      <span>手机抖音扫一下二维码即可，全程用你自己的会话</span>
                    </div>
                  </li>
                  <li>
                    <span className="cnum">2</span>
                    <div>
                      <b>拉取你的「喜欢」</b>
                      <span>后台采集你点过赞的内容，进度实时可见</span>
                    </div>
                  </li>
                  <li>
                    <span className="cnum">3</span>
                    <div>
                      <b>算法 + AI 双重提炼</b>
                      <span>先按兴趣分类打分聚合，再由 AI 写成完整画像；答 3–5 道小题还能精修</span>
                    </div>
                  </li>
                  <li>
                    <span className="cnum">4</span>
                    <div>
                      <b>一张完整的你</b>
                      <span>主标签、子兴趣、兴趣领域、成局提示，一屏看完</span>
                    </div>
                  </li>
                </ol>
                <div className="lp-persona-demo" aria-label="画像示例">
                  <span className="lp-persona-tag">探索型 Builder</span>
                  <div className="lp-persona-chips">
                    <span>知识策展人</span>
                    <span>审美观察者</span>
                    <span>黑客松 / AI 创变</span>
                    <span>华强北硬件</span>
                    <span>运动康复</span>
                  </div>
                  <span className="lp-persona-note">↑ 一份真实生成的画像示例</span>
                </div>
                <p className="lp-story-so">
                  画像直接参与搭子匹配与比赛推荐——相似度里多了「口味」这一维，
                  成局后队友能看到你的兴趣 chips。默认仅局内可见，随时可以一键删除。
                </p>
              </article>
            </div>
          </div>
        </section>

        {/* ---------- 怎么成局 ---------- */}
        <section className="lp-section" id="how">
          <div className="lp-container">
            <div className="lp-section-head">
              <span className="lp-kicker">怎么成局</span>
              <h2>三步，从「差一个」到「成局」</h2>
              <p>
                你只负责说清楚想做的事，剩下的交给噜噜：找人、对时间、订场地、发提醒。
              </p>
            </div>
            <div className="lp-steps">
              <article className="lp-step">
                <span className="no">01</span>
                <LuluSprite clip="intent.card" size={150} />
                <h3>说清你差什么</h3>
                <p>
                  一句话发意图，噜噜用两轮澄清把它变成明确的局：做什么、什么时候、
                  在哪个校区、差几个人、需要什么角色。
                </p>
                <span className="tag">匿名发布 · 随时可撤回</span>
              </article>
              <article className="lp-step">
                <span className="no">02</span>
                <LuluSprite clip="pool.waiting" size={150} />
                <h3>噜噜安静找齐</h3>
                <p>
                  意图进入撮合池，按共同空档、校区可达性与能力互补匹配合适的人。
                  人没齐不打扰你，找齐了才叫你。
                </p>
                <span className="tag">不看脸 · 只看事</span>
              </article>
              <article className="lp-step">
                <span className="no">03</span>
                <LuluSprite clip="confirm.gather" size={150} />
                <h3>全员点头，才成局</h3>
                <p>
                  每个人确认后才建局。研讨室、场馆这类预约由行动代理先出预览、
                  全员确认后再执行，改约和补位也有人管。
                </p>
                <span className="tag">预约自动办 · 提醒不缺席</span>
              </article>
            </div>
          </div>
        </section>

        {/* ---------- 能做什么 ---------- */}
        <section className="lp-section" id="features">
          <div className="lp-container">
            <div className="lp-section-head">
              <span className="lp-kicker">能做什么</span>
              <h2>一个入口成局，一个助手跑腿</h2>
              <p>
                「⊕ 差一个」负责把人凑齐；「今天」里的 hermes 负责你自己的校园事务。
                比赛、消息、信任体系围绕这两件事展开。
              </p>
            </div>
            <div className="lp-features">
              <article className="lp-feature">
                <div className="icon">
                  <img src={assetURL("/assets/stickers/chair-empty.png")} alt="" loading="lazy" />
                </div>
                <div>
                  <h3>
                    ⊕ 差一个
                    <span className="pill">成局入口</span>
                  </h3>
                  <p>
                    运动、自习、饭搭、拼车，到正式比赛组队——说出缺口，等噜噜补齐。
                    发起、确认、改约、补位、复局，一个状态机管到底。
                  </p>
                </div>
              </article>
              <article className="lp-feature">
                <div className="icon">
                  <img src={assetURL("/assets/stickers/desk-calendar.png")} alt="" loading="lazy" />
                </div>
                <div>
                  <h3>
                    今天
                    <span className="pill">私有校园执行器</span>
                  </h3>
                  <p>
                    课表、空教室、场馆空档、作业 DDL、校车班次，问一句就有答案。
                    hermes 只为你一个人干活，用的是你自己的授权。
                  </p>
                </div>
              </article>
              <article className="lp-feature">
                <div className="icon">
                  <img src={assetURL("/assets/stickers/trophy.png")} alt="" loading="lazy" />
                </div>
                <div>
                  <h3>
                    比赛雷达
                    <span className="pill">组队场景</span>
                  </h3>
                  <p>
                    经人工核验的赛事库，标注报名截止与能力缺口；支持正式组队，
                    个人赛也能找到备赛搭子。
                  </p>
                </div>
              </article>
              <article className="lp-feature">
                <div className="icon">
                  <img src={assetURL("/assets/stickers/badge.png")} alt="" loading="lazy" />
                </div>
                <div>
                  <h3>
                    信任与安全
                    <span className="pill">T0–T4</span>
                  </h3>
                  <p>
                    校园实名认证起步，信任等级随真实赴约成长；分项授权、随时撤回、
                    级联清除，举报与屏蔽全程可用。
                  </p>
                </div>
              </article>
            </div>
          </div>
        </section>

        {/* ---------- 我们不做的事 ---------- */}
        <section className="lp-section" id="principles">
          <div className="lp-container">
            <div className="lp-principles">
              <div>
                <span className="lp-kicker">产品红线</span>
                <h2>噜噜不做的事，和做的事一样重要。</h2>
                <p className="intro">
                  我们反对把人变成货架上的商品。噜噜不介绍人、不运营关系——
                  关系应该在一起做成一件事之后自然发生。
                </p>
                <figure className="bow">
                  <LuluSprite clip="exit.bow" size={110} />
                  <figcaption>局成之后，噜噜鞠躬退场，把位置留给你们。</figcaption>
                </figure>
              </div>
              <ul className="lp-noes">
                <li>
                  <span className="x" aria-hidden>
                    ✕
                  </span>
                  <div>
                    <b>没有好友申请，也没有「可能认识的人」</b>
                    <span>关系只能通过一起完成一件事产生。</span>
                  </div>
                </li>
                <li>
                  <span className="x" aria-hidden>
                    ✕
                  </span>
                  <div>
                    <b>不给人打分</b>
                    <span>共同经历只记「做过什么」，绝不记录「这个人怎么样」。</span>
                  </div>
                </li>
                <li>
                  <span className="x" aria-hidden>
                    ✕
                  </span>
                  <div>
                    <b>没有已读回执，没有在线状态</b>
                    <span>消息不制造社交压力，什么时候回，由你决定。</span>
                  </div>
                </li>
                <li>
                  <span className="x" aria-hidden>
                    ✕
                  </span>
                  <div>
                    <b>匿名进池，不看脸挑人</b>
                    <span>报名者与报名人数彼此不可见，匹配只看空档与能力。</span>
                  </div>
                </li>
                <li>
                  <span className="x" aria-hidden>
                    ✕
                  </span>
                  <div>
                    <b>红灯操作永不代理</b>
                    <span>成绩、选课、请假、支付——在架构上就到不了。</span>
                  </div>
                </li>
                <li>
                  <span className="x" aria-hidden>
                    ✕
                  </span>
                  <div>
                    <b>不做 AI 陪伴</b>
                    <span>成局后噜噜退场，只在提醒、改约、补位或被 @ 时出现。</span>
                  </div>
                </li>
              </ul>
            </div>
          </div>
        </section>

        {/* ---------- FAQ ---------- */}
        <section className="lp-section" id="faq">
          <div className="lp-container">
            <div className="lp-section-head">
              <span className="lp-kicker">常见问题</span>
              <h2>你可能想问</h2>
            </div>
            <div className="lp-faq">
              {FAQS.map((item, i) => (
                <details key={item.q} open={i === 0}>
                  <summary>
                    {item.q}
                    <span className="plus" aria-hidden>
                      ＋
                    </span>
                  </summary>
                  {item.a}
                </details>
              ))}
            </div>
          </div>
        </section>

        {/* ---------- 尾部 CTA ---------- */}
        <section className="lp-section" style={{ paddingTop: 0 }}>
          <div className="lp-container">
            <div className="lp-cta-band">
              <h2>差一个？现在就发。</h2>
              <p>下一次「三缺一」的时候，别再挨个问了——告诉噜噜，等它叫你。</p>
              <Link className="lp-btn lg" to="/app" data-od-id="landing-cta-bottom">
                打开噜噜成局
              </Link>
            </div>
          </div>
        </section>
      </main>

      {/* ---------- 页脚 ---------- */}
      <footer className="lp-footer">
        <div className="lp-container">
          <div className="lp-footer-grid">
            <div>
              <span className="lp-brand">
                <img src={APP_ICON} alt="" />
                噜噜成局
              </span>
              <p className="slogan">
                AI 不介绍人，AI 促成事。差一个，就成局。
                <br />
                工程代号 ONE MORE。
              </p>
            </div>
            <div>
              <h4>产品</h4>
              <ul>
                <li>
                  <Link to="/app">打开网页版</Link>
                </li>
                <li>
                  <a href="#story">前情提要</a>
                </li>
                <li>
                  <a href="#how">怎么成局</a>
                </li>
                <li>
                  <a href="#features">能做什么</a>
                </li>
                <li>
                  <a href="#faq">常见问题</a>
                </li>
              </ul>
            </div>
            <div>
              <h4>支持与法律</h4>
              <ul>
                <li>
                  <Link to="/legal/privacy">隐私政策</Link>
                </li>
                <li>
                  <Link to="/legal/terms">用户协议</Link>
                </li>
                <li>
                  <Link to="/app">应用内反馈（我 → 申诉）</Link>
                </li>
              </ul>
            </div>
          </div>
          <div className="lp-footer-bottom">
            <span>© 2026 噜噜成局 · 校园成局智能体</span>
            <span>面向所有在校学生 · 中山大学深度定制 · 非学校官方服务</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
