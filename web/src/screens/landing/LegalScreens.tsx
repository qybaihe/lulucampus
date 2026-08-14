import { useEffect, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { assetURL } from "../../core/assets";
import { WebAppLink } from "./WebAppLink";

/**
 * 法律文档页（隐私政策 / 用户协议）。
 * 与 Landing 共用 lp- 版式；条款事实与 README「服务端强制的产品红线」、
 * docs/00_产品方案_V2.1.md 保持一致。
 */

const APP_ICON = assetURL("/assets/landing/app-icon.png");
const UPDATED_AT = "2026年8月12日";

function LegalLayout({
  title,
  lede,
  children,
}: {
  title: string;
  lede: ReactNode;
  children: ReactNode;
}) {
  useEffect(() => {
    const prev = document.title;
    document.title = `${title} — 噜噜成局`;
    window.scrollTo(0, 0);
    return () => {
      document.title = prev;
    };
  }, [title]);

  return (
    <div className="lp" data-od-id="legal-root">
      <header className="lp-header">
        <div className="lp-container lp-header-inner">
          <Link className="lp-brand" to="/" aria-label="返回噜噜成局首页">
            <img src={APP_ICON} alt="" />
            噜噜成局
          </Link>
          <div className="lp-header-cta">
            <Link className="lp-btn ghost sm" to="/">
              返回首页
            </Link>
            <WebAppLink className="lp-btn primary sm">打开网页版</WebAppLink>
          </div>
        </div>
      </header>

      <main className="lp-legal-main">
        <article className="lp-container lp-legal">
          <h1>{title}</h1>
          <p className="updated">最近更新：{UPDATED_AT} · 适用于噜噜成局网页版与 iOS 客户端</p>
          <div className="lede">{lede}</div>
          {children}
        </article>
      </main>

      <footer className="lp-footer">
        <div className="lp-container lp-footer-bottom" style={{ borderTop: "none", marginTop: 0, paddingTop: 0 }}>
          <span>© 2026 噜噜成局 · 校园成局智能体</span>
          <span>
            <Link to="/legal/privacy">隐私政策</Link>
            {" · "}
            <Link to="/legal/terms">用户协议</Link>
            {" · "}
            <Link to="/">返回首页</Link>
          </span>
        </div>
      </footer>
    </div>
  );
}

export function PrivacyPolicyScreen() {
  return (
    <LegalLayout
      title="隐私政策"
      lede={
        <>
          一句话版本：噜噜成局只为「促成局」收集必要的数据；每一类数据单独授权、
          随时可撤回，撤回即级联清除。我们不读取成绩，不向他人展示你的信任等级，
          不记录任何「对人的评价」。
        </>
      }
    >
      <section>
        <h2>1. 我们收集哪些信息</h2>
        <ul>
          <li>
            <b>校园身份事实：</b>在你通过学校统一身份扫码授权后，我们读取姓名、学号、
            院系、年级、校区等基本事实，用于校园实名认证与成局展示（他人仅见必要信息）。
          </li>
          <li>
            <b>课表与空档：</b>授权后一次性扫描全学期课表并缓存，每周做增量校验。
            课表用于计算「共同空档」——匹配时只交换某个时段是否有空，不交换课表内容。
          </li>
          <li>
            <b>你主动填写的资料：</b>能力标签、自述、匹配偏好，以及可选导入的兴趣画像
            （例如抖音兴趣标签，仅用于口味相近的搭子匹配，可随时删除）。
          </li>
          <li>
            <b>成局记录：</b>你发布的意图、参与的局、局内消息与共同经历（只记事实）。
          </li>
          <li>
            <b>设备与日志：</b>请求标识、错误日志等运行数据，用于排障与安全审计。
          </li>
        </ul>
      </section>

      <section>
        <h2>2. 分项授权与撤回</h2>
        <p>
          身份、课表、场馆预约等每一类校园能力都是<b>单独授权</b>的，没有一揽子勾选。
          你可以随时在「我 → 授权管理」中关闭任何一项；<b>撤回会级联清除</b>由该授权
          产生的数据（例如撤回课表授权即删除课表缓存与空档索引）。
        </p>
      </section>

      <section>
        <h2>3. 我们如何使用这些信息</h2>
        <ul>
          <li>撮合成局：按共同空档、校区可达性与能力互补计算候选。</li>
          <li>执行校园动作：以你自己的授权查询课表、空教室、场馆、班车、作业截止时间，并在全员确认后代为预约。</li>
          <li>信任体系：根据实名认证与真实赴约记录计算你的 T0–T4 信任等级（仅你自己可见）。</li>
          <li>大模型的使用被严格限定为两件事：把你的话编译成结构化意图、生成匹配理由说明——<b>不参与匹配打分，不接触执行</b>。</li>
        </ul>
      </section>

      <section>
        <h2>4. 我们明确不做的事</h2>
        <ul>
          <li>不读取、不存储任何成绩数据。</li>
          <li>空档交集不携带身份信息；撮合池中报名者与报名人数互不可见。</li>
          <li>不向任何人展示你的信任等级，也不提供查询他人信任等级的接口。</li>
          <li>消息没有已读回执、没有在线状态、没有「正在输入」。</li>
          <li>共同经历账本只记录「一起做过什么」，不含评价、印象、标签或备注。</li>
          <li>不做用户搜索、好友推荐，不基于历史记录向你主动推销新的局。</li>
        </ul>
      </section>

      <section>
        <h2>5. 信息共享与披露</h2>
        <p>
          我们<b>不出售</b>你的个人信息。只有在成局必需的最小范围内，同局成员可以看到
          你的展示名与承担的角色。行动代理调用校园系统时使用<b>你自己的凭证</b>，
          凭证以主密钥加密存放在独立保管库中，执行完毕即卸载；执行范围被白名单
          Action Schema 严格限定，写操作必须经过全员确认。
        </p>
      </section>

      <section>
        <h2>6. 数据保留、导出与删除</h2>
        <ul>
          <li>数据仅在提供服务所需期间保留；赛事等外部信息过期自动下架。</li>
          <li>你可以在「我 → 账号」发起<b>数据导出</b>，获得一份可读的个人数据副本。</li>
          <li>你可以随时<b>注销账号</b>：注销走完整闭环，清除身份事实、课表缓存、意图与偏好等个人数据。</li>
        </ul>
      </section>

      <section>
        <h2>7. Cookie 与本地存储</h2>
        <p>
          网页版仅使用本地存储保存你的登录会话令牌与界面偏好（例如是否看过引导页），
          不使用第三方跟踪或广告 Cookie。
        </p>
      </section>

      <section>
        <h2>8. 政策变更与联系我们</h2>
        <p>
          政策更新会在本页公布并标注日期；涉及数据用途的重大变更会在应用内提示。
          如有疑问或申诉，请使用应用内「我 → 申诉」渠道联系我们。
        </p>
      </section>
    </LegalLayout>
  );
}

export function TermsScreen() {
  return (
    <LegalLayout
      title="用户协议"
      lede={
        <>
          噜噜成局帮助在校学生把「差一个人」的事组起来。使用本服务即表示你
          同意以下条款——核心只有一条：<b>认真赴约，尊重同局的每一个人</b>。
        </>
      }
    >
      <section>
        <h2>1. 服务说明</h2>
        <p>
          噜噜成局（工程代号 ONE MORE）提供校园成局撮合、比赛组队、校园事务查询与
          预约协助。服务由网页版与 iOS 客户端提供，连接同一套后端。本服务面向所有
          在校学生，对中山大学做了深度定制优化；本服务为校园项目，
          <b>并非任何学校的官方服务</b>。
        </p>
      </section>

      <section>
        <h2>2. 使用资格与账号</h2>
        <ul>
          <li>你需要是在校学生或教职工，并完成校园身份认证；中山大学用户可通过学校统一身份扫码认证。</li>
          <li>账号与校园身份绑定，仅限本人使用，不得转借、出售或冒用。</li>
          <li>你对账号下的行为负责；发现异常请立即在应用内反馈。</li>
        </ul>
      </section>

      <section>
        <h2>3. 成局行为规范</h2>
        <ul>
          <li>发布真实、明确的意图；不得发布违法违规、商业推广或与校园生活无关的内容。</li>
          <li>确认加入即承诺到场；无法到场请尽早发起改约或退出，让补位机制接手。</li>
          <li>无故爽约、骚扰、歧视等行为会计入安全记录，影响信任等级，情节严重的将被限制成局或封禁。</li>
          <li>你可以随时举报或屏蔽任何用户；被屏蔽双方不会再被匹配到同一个局。</li>
        </ul>
      </section>

      <section>
        <h2>4. 行动代理的边界</h2>
        <ul>
          <li>查询类操作（课表、空教室、场馆空档、班车等）在你授权后自动执行。</li>
          <li>预约类写操作必须先出预览、经<b>全员确认</b>后才会提交，全程可审计。</li>
          <li>请假、选课、成绩、支付、简历投递等操作在架构上被永久切断，噜噜不会也无法代理。</li>
        </ul>
      </section>

      <section>
        <h2>5. 内容与知识产权</h2>
        <p>
          你发布的内容归你所有；为提供服务，你授予我们在服务范围内存储、展示该内容的
          许可。噜噜形象、品牌与产品设计归项目所有，未经许可不得用于其他用途。
        </p>
      </section>

      <section>
        <h2>6. 免责声明</h2>
        <ul>
          <li>线下活动请注意人身与财产安全，风险由参与者自行承担；请优先选择校内公共场所。</li>
          <li>赛事信息经人工核验，但报名条件与截止时间以主办方官方发布为准。</li>
          <li>课表、场馆等数据来自校园系统，可能存在延迟或临时调整，请以学校系统为准。</li>
          <li>服务按「现状」提供；因校园系统维护等原因导致的中断，我们会尽快恢复但不承担由此产生的损失。</li>
        </ul>
      </section>

      <section>
        <h2>7. 服务变更与终止</h2>
        <p>
          我们可能调整或下线部分功能，重大变更会提前在应用内通知。你可以随时停止使用
          并注销账号；注销后个人数据按<Link to="/legal/privacy">《隐私政策》</Link>清除。
          对违反本协议的账号，我们有权采取限制成局、屏蔽或封禁等措施。
        </p>
      </section>

      <section>
        <h2>8. 其他</h2>
        <p>
          本协议的订立与履行适用中华人民共和国法律。协议更新会在本页公布；
          继续使用服务即视为接受更新后的条款。如有疑问，请通过应用内「我 → 申诉」联系我们。
        </p>
      </section>
    </LegalLayout>
  );
}
