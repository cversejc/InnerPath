<template>
  <Teleport to="body">
    <div class="legal-dialog-layer" @click.self="close">
      <section
        ref="dialog"
        class="legal-dialog"
        role="dialog"
        aria-modal="true"
        tabindex="-1"
        :aria-labelledby="titleId"
        @keydown="handleKeydown"
      >
        <header class="legal-dialog-header">
          <div>
            <p class="legal-dialog-kicker">辰鉴 · 文档草案</p>
            <h2 :id="titleId">{{ document.title }}</h2>
          </div>
          <button ref="closeButton" class="legal-close-button" type="button" aria-label="关闭协议" @click="close">×</button>
        </header>

        <div class="legal-document-scroll" tabindex="0">
          <p class="legal-template-notice">
            当前为模板草案。运营主体、服务范围、数据处理安排及联系渠道等内容待确认，正式上线前请完成核实、替换和审阅。
          </p>
          <p class="legal-document-date">发布日期 / 更新日期：[待确认]</p>

          <section v-for="section in document.sections" :key="section.title" class="legal-document-section">
            <h3>{{ section.title }}</h3>
            <p v-for="paragraph in section.paragraphs" :key="paragraph">{{ paragraph }}</p>
          </section>
        </div>

        <footer class="legal-dialog-footer">
          <button class="legal-done-button" type="button" @click="close">关闭并返回</button>
        </footer>
      </section>
    </div>
  </Teleport>
</template>

<script>
const documents = {
  terms: {
    title: '用户协议',
    sections: [
      {
        title: '一、协议主体与服务',
        paragraphs: [
          '本协议由 [运营主体全称，待确认]（以下简称“我们”）与辰鉴平台用户订立。运营主体名称、注册地址及联系方式须在正式上线前补充。',
          '辰鉴平台根据实际开放情况提供账号管理、个人资料管理、人生说明书或其他报告、咨询预约、决策日历及相关服务。具体服务内容以页面展示和另行说明为准。'
        ]
      },
      {
        title: '二、账号注册与安全',
        paragraphs: [
          '你应使用本人可正常接收短信的手机号注册，并按页面要求提供真实、准确的信息。请妥善保管账号、密码和验证码，不得出租、出借或以其他方式交由他人使用。',
          '如发现账号被未经授权使用或存在安全风险，请及时通过本协议列明的联系渠道通知我们。因你未妥善保管凭据造成的损失，责任承担以适用法律规定和具体情况为准。'
        ]
      },
      {
        title: '三、服务内容与使用边界',
        paragraphs: [
          '平台报告、分析和建议基于你提交的信息及相应服务流程形成，部分内容可能由算法生成并由工作人员处理或审校。相关内容仅供个人成长与信息参考，不构成医疗诊断、心理治疗、法律、投资或其他专业意见，也不保证特定结果。',
          '你应结合自身情况独立判断并作出决定。涉及健康、安全或其他专业事项时，请向具备相应资质的专业人士寻求帮助。'
        ]
      },
      {
        title: '四、用户行为规范',
        paragraphs: [
          '你不得利用平台从事违反法律法规、侵害他人合法权益、干扰平台运行或破坏数据安全的行为，也不得提交依法不得处理或明显与服务无关的他人信息。',
          '如你的行为可能造成安全风险或违反本协议，我们可在法律允许范围内采取提醒、限制功能、暂停或终止服务等措施，并依法处理相关信息。'
        ]
      },
      {
        title: '五、内容与知识产权',
        paragraphs: [
          '平台的软件、界面、标识、文字及其他内容的权利归我们或相应权利人所有。未经许可，你不得复制、传播、改编或用于商业用途。',
          '你对自行提交内容依法享有相应权利，并确认提交内容不侵害他人权益。为向你提供服务所必需，我们可在合理范围内处理该内容；具体处理方式以《隐私条款》为准。'
        ]
      },
      {
        title: '六、服务调整与中断',
        paragraphs: [
          '我们可能因维护、升级、安全处置、法律要求或其他合理原因调整、中止部分服务，并在可行时通过平台通知。涉及用户重要权益的变更，将依法履行告知义务。'
        ]
      },
      {
        title: '七、协议更新与争议处理',
        paragraphs: [
          '我们可根据服务变化或法律要求更新本协议，并通过合理方式提示你。更新后的协议生效时间及不同意时的处理方式，应在正式版本中明确。',
          '本协议适用法律、争议解决方式及管辖地点：[待法务确认后补充]。本条不影响你依法享有的消费者及个人信息相关权利。'
        ]
      },
      {
        title: '八、联系我们',
        paragraphs: [
          '如对本协议有疑问，请联系：[客服邮箱或其他渠道，待补充]；运营主体：[待补充]。'
        ]
      }
    ]
  },
  privacy: {
    title: '隐私条款',
    sections: [
      {
        title: '一、个人信息处理者',
        paragraphs: [
          '辰鉴平台个人信息处理者为 [运营主体全称，待确认]。本模板中的处理目的、信息范围、接收方、保存期限和联系渠道均须结合正式部署逐项核实。'
        ]
      },
      {
        title: '二、我们处理的信息',
        paragraphs: [
          '账号与认证信息：手机号、姓名、密码验证凭据、验证码请求记录，以及登录时间、IP 地址、浏览器或设备信息等账号安全记录。密码应以不可逆的安全方式保存。',
          '个人资料：你主动填写的性别、出生日期和时间、出生地、居住地、婚姻或职业教育情况、个性特征、优势与局限、偏好及使用场景等信息；具体字段以产品实际页面为准。',
          '服务记录：咨询预约所需的联系方式、意向时间、关注议题和备注；服务申请、报告或日历生成所需的资料、补充说明、处理进度及交付内容。',
          '请仅提交完成相应服务所需的信息。部分资料是否构成敏感个人信息及是否需要单独同意，应由运营主体在正式上线前评估并落实。'
        ]
      },
      {
        title: '三、处理目的',
        paragraphs: [
          '我们处理上述信息，用于创建和维护账号、身份验证与安全保护、管理个人资料、响应预约或服务申请、生成并交付报告或日历、提供客户支持，以及履行法律义务。超出这些目的的处理应另行说明并依法取得相应授权。'
        ]
      },
      {
        title: '四、受托处理与信息提供',
        paragraphs: [
          '短信验证：当前后端配置使用 Spug 短信服务发送验证码。正式版本需补充受托方主体、提供给对方的信息、处理地点、保存期限及安全安排。',
          '报告或日历草稿生成：当前后端配置使用 DeepSeek API 处理相关 AI 生成请求。生成请求可能包含完成服务所需的个人资料或申请内容。正式上线前须核实实际发送字段、服务主体、处理地点、保存期限及是否涉及个人信息出境，并依法完成告知和授权。',
          '为完成咨询或服务交付，获授权的工作人员可能访问相关申请和资料。除受托处理、履行服务所必需或法律法规允许的情形外，向其他主体提供个人信息前，我们将依法履行告知和取得同意等义务。'
        ]
      },
      {
        title: '五、保存期限与安全措施',
        paragraphs: [
          '个人信息保存地点：[待确认]；各类信息的保存期限：[按业务目的和法定义务逐项补充]。达到保存期限或处理目的后，我们将依法删除或匿名化处理，法律法规另有规定的除外。',
          '我们将采取与处理目的相适应的管理和技术措施保护信息，并限制工作人员按需访问。发生或可能发生个人信息安全事件时，将依法采取补救措施并履行通知义务。'
        ]
      },
      {
        title: '六、你的权利',
        paragraphs: [
          '你可以依法请求查询、复制、更正或删除个人信息，撤回已作出的同意，限制或拒绝特定处理，并申请注销账号。你可通过 [客服邮箱或其他渠道，待补充] 提交请求；我们将在核验身份后依法处理并反馈。',
          '撤回同意不影响撤回前基于同意已进行的处理。删除或注销可能影响部分服务的继续使用；依法需要留存的信息将在必要期限内隔离保存。'
        ]
      },
      {
        title: '七、未成年人保护',
        paragraphs: [
          '如服务涉及不满十四周岁的未成年人个人信息，我们将在监护人同意后处理，并制定专门规则。产品是否面向未成年人、年龄核验和监护人同意流程：[待运营主体确认并补充]。'
        ]
      },
      {
        title: '八、条款更新与联系',
        paragraphs: [
          '我们会在本页面展示隐私条款的更新版本，并依法提示对你权益有重大影响的变更。',
          '如对个人信息处理有疑问、意见或请求，请联系：[个人信息保护联系邮箱或其他渠道，待补充]；运营主体：[待补充]。'
        ]
      }
    ]
  }
}

export default {
  name: 'LegalDocumentDialog',
  props: {
    type: {
      type: String,
      required: true,
      validator: value => ['terms', 'privacy'].includes(value)
    }
  },
  emits: ['close'],
  computed: {
    document() {
      return documents[this.type] || documents.terms
    },
    titleId() {
      return `legal-document-${this.type}-title`
    }
  },
  mounted() {
    this.$nextTick(() => this.$refs.closeButton?.focus({ preventScroll: true }))
  },
  methods: {
    close() {
      this.$emit('close')
    },
    handleKeydown(event) {
      if (event.key === 'Escape') {
        event.preventDefault()
        this.close()
        return
      }
      if (event.key !== 'Tab') return

      const focusable = [...this.$refs.dialog.querySelectorAll('button:not([disabled]), [tabindex="0"]')]
        .filter(element => element.getClientRects().length > 0)
      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      if (!first || !last) {
        event.preventDefault()
      } else if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }
  }
}
</script>

<style scoped>
.legal-dialog-layer {
  position: fixed;
  z-index: 1200;
  inset: 0;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(38, 33, 29, 0.52);
  backdrop-filter: blur(4px);
}

.legal-dialog {
  display: flex;
  width: min(100%, 720px);
  max-height: min(840px, 88dvh);
  flex-direction: column;
  overflow: hidden;
  border: 1px solid rgba(139, 90, 20, 0.2);
  border-radius: 8px;
  background: #fffdf8;
  color: var(--ink, #2f241b);
  box-shadow: 0 28px 90px rgba(38, 33, 29, 0.28);
}

.legal-dialog-header {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  border-bottom: 1px solid rgba(139, 90, 20, 0.14);
  padding: 18px 24px;
}

.legal-dialog-kicker {
  margin: 0 0 3px;
  color: var(--cinnabar-deep, #9e3f35);
  font-size: 12px;
  font-weight: 700;
}

.legal-dialog-header h2 {
  margin: 0;
  color: var(--ink, #2f241b);
  font-family: var(--font-display, serif);
  font-size: 24px;
  line-height: 1.35;
}

.legal-close-button {
  display: grid;
  width: 40px;
  height: 40px;
  flex: 0 0 auto;
  place-items: center;
  border: 1px solid rgba(139, 90, 20, 0.2);
  border-radius: 6px;
  background: transparent;
  color: var(--ink-soft, #614d3d);
  cursor: pointer;
  font-family: var(--font-ui, sans-serif);
  font-size: 24px;
  line-height: 1;
}

.legal-close-button:hover,
.legal-close-button:focus-visible {
  border-color: var(--cinnabar, #b5574c);
  color: var(--cinnabar-deep, #9e3f35);
}

.legal-document-scroll {
  min-height: 0;
  flex: 1 1 auto;
  overflow: auto;
  overscroll-behavior: contain;
  padding: 20px 28px 28px;
  scrollbar-color: rgba(139, 90, 20, 0.35) transparent;
  scrollbar-width: thin;
}

.legal-template-notice {
  margin: 0 0 12px;
  border-left: 3px solid var(--gold, #d9ba62);
  padding: 10px 12px;
  background: rgba(217, 186, 98, 0.13);
  color: var(--ink-soft, #614d3d);
  font-size: 13px;
  line-height: 1.75;
}

.legal-document-date {
  margin: 0 0 22px;
  color: #858b8e;
  font-size: 12px;
}

.legal-document-section {
  margin-top: 20px;
}

.legal-document-section h3 {
  margin: 0 0 8px;
  color: var(--cinnabar-deep, #9e3f35);
  font-size: 15px;
  font-weight: 700;
  line-height: 1.55;
}

.legal-document-section p {
  margin: 0 0 8px;
  color: var(--ink-soft, #614d3d);
  font-size: 14px;
  line-height: 1.85;
  overflow-wrap: anywhere;
}

.legal-dialog-footer {
  display: flex;
  flex: 0 0 auto;
  justify-content: flex-end;
  border-top: 1px solid rgba(139, 90, 20, 0.14);
  padding: 12px 24px;
}

.legal-done-button {
  min-width: 112px;
  min-height: 42px;
  border: 1px solid rgba(158, 63, 53, 0.42);
  border-radius: 5px;
  padding: 0 16px;
  background: var(--cinnabar-deep, #9e3f35);
  color: #fffdf8;
  cursor: pointer;
  font: inherit;
  font-size: 14px;
  font-weight: 700;
}

.legal-done-button:hover,
.legal-done-button:focus-visible {
  background: #84352e;
}

.legal-dialog :focus-visible {
  outline: 2px solid var(--cinnabar, #b5574c);
  outline-offset: 3px;
}

@media (max-width: 540px) {
  .legal-dialog-layer {
    padding:
      max(12px, env(safe-area-inset-top, 0px))
      max(12px, env(safe-area-inset-right, 0px))
      max(12px, env(safe-area-inset-bottom, 0px))
      max(12px, env(safe-area-inset-left, 0px));
  }

  .legal-dialog {
    max-height: 100%;
  }

  .legal-dialog-header {
    padding: 14px 16px;
  }

  .legal-dialog-header h2 {
    font-size: 21px;
  }

  .legal-document-scroll {
    padding: 16px 18px 22px;
  }

  .legal-document-section {
    margin-top: 18px;
  }

  .legal-dialog-footer {
    padding: 10px 16px max(10px, env(safe-area-inset-bottom, 0px));
  }
}

@media (prefers-reduced-motion: reduce) {
  .legal-dialog-layer {
    backdrop-filter: none;
  }
}
</style>
