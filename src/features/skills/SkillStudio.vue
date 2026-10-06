<template>
  <div class="skill-studio-shell" :class="{ 'is-mobile-nav-open': mobileNavOpen }">
    <aside class="studio-rail" :class="{ 'is-open': mobileNavOpen }" aria-label="技能工作台导航">
      <div class="studio-rail-brand">
        <router-link class="studio-brand-lockup" :to="studioReturnLocation" :aria-label="`返回${isAdmin ? '运营中枢' : '咨询工作台'}`" @click="closeMobileNav">
          <picture>
            <source srcset="/brand-emblem.webp" type="image/webp">
            <img src="/brand-emblem.png" alt="" width="214" height="256" decoding="async">
          </picture>
          <span><strong>辰鉴</strong><small>技能工作台</small></span>
        </router-link>
        <span class="studio-rail-status"><i></i>{{ isAdmin ? 'ADMIN STUDIO' : 'CONSULTANT STUDIO' }}</span>
      </div>
      <nav class="studio-rail-nav" aria-label="工作台切换">
        <p class="studio-rail-label">工作台切换</p>
        <router-link class="studio-rail-item active" :to="studioReturnLocation" @click="closeMobileNav">
          <IconMark name="arrow-left" /><span>返回{{ isAdmin ? '运营中枢' : '咨询工作台' }}</span>
        </router-link>
        <router-link v-if="isAdmin" class="studio-rail-item" to="/staff" @click="closeMobileNav">
          <IconMark name="reports" /><span>咨询工作台</span>
        </router-link>
        <router-link v-else class="studio-rail-item" to="/staff" @click="closeMobileNav">
          <IconMark name="reports" /><span>报告申请</span>
        </router-link>
      </nav>
      <div class="studio-rail-footer">
        <div class="studio-operator">
          <span class="studio-operator-avatar">{{ operatorInitial }}</span>
          <span><strong>{{ operatorName }}</strong><small>{{ isAdmin ? '系统管理员' : '咨询师' }}</small></span>
        </div>
        <VanButton class="studio-rail-logout" type="default" plain native-type="button" :disabled="loggingOut" :loading="loggingOut" loading-text="退出中…" :aria-busy="loggingOut" @click="handleLogout">
          <template #icon><IconMark name="logout" /></template>
          退出登录
        </VanButton>
      </div>
    </aside>
    <button v-if="mobileNavOpen" type="button" class="studio-rail-scrim" aria-label="关闭技能工作台导航" @click="closeMobileNav"></button>

    <div class="skill-studio-app">
      <main class="skill-studio-main">
      <header class="studio-heading">
        <div class="studio-heading-leading">
          <VanButton class="studio-menu-toggle" type="default" plain native-type="button" aria-label="打开技能工作台导航" :aria-expanded="mobileNavOpen" @click="toggleMobileNav">
            <template #icon><IconMark name="settings" /></template>
          </VanButton>
          <div class="studio-breadcrumb" aria-label="当前位置"><span>技能工作台</span><IconMark name="arrow" /><strong>{{ isAdmin ? '管理员维护' : '咨询师参考' }}</strong></div>
        </div>
        <h1>技能与示例工作台</h1>
        <div class="studio-heading-actions">
          <span class="studio-role-chip">{{ isAdmin ? "管理员维护" : "咨询师参考" }}</span>
          <router-link class="studio-return-link" :to="studioReturnLocation">返回{{ isAdmin ? '运营中枢' : '咨询工作台' }}</router-link>
        </div>
      </header>
      <p
        v-if="message"
        class="studio-message"
        :class="{ error: messageKind === 'error' }"
        role="status"
      >
        {{ message }}
      </p>
      <div class="studio-workspace">
        <aside class="skill-catalog" aria-label="AI 技能目录">
          <h2>AI 技能目录</h2>
          <p>覆盖报告分析与决策日历各步骤</p>
          <label class="mobile-skill-select"
            >选择技能<select
              :value="selectedSkillKey"
              @change="selectSkill($event.target.value)"
            >
              <option
                v-for="skill in catalog"
                :key="skill.key"
                :value="skill.key"
              >
                {{ skill.node }} · {{ skill.name }}
              </option>
            </select></label
          >
          <div class="skill-catalog-list">
            <button
              v-for="skill in catalog"
              :key="skill.key"
              type="button"
              :aria-pressed="selectedSkillKey === skill.key"
              :class="{ selected: selectedSkillKey === skill.key }"
              @click="selectSkill(skill.key)"
            >
              <small
                >{{ skill.step ? `第 ${skill.step.slice(1)} 步 · ` : ""
                }}{{ skill.node }}</small
              ><strong>{{ skill.name }}</strong>
            </button>
          </div>
        </aside>
        <section class="studio-working-area" aria-label="当前技能工作区">
          <div class="studio-work-toolbar">
            <div class="selected-skill-heading">
              <h2>{{ selectedSkill.name }}</h2>
              <div v-if="isAdmin" class="version-selector">
                <label for="studio-version">版本</label
                ><select
                  id="studio-version"
                  :value="selectedVersion?.id || ''"
                  @change="selectVersionById($event.target.value)"
                >
                  <option v-if="!skillVersions.length" value="">
                    暂无版本
                  </option>
                  <option
                    v-for="version in skillVersions"
                    :key="version.id"
                    :value="version.id"
                  >
                    第 {{ version.version }} 版 ·
                    {{ VERSION_STATUS_LABELS[version.status] || "未知状态" }}
                  </option></select
                ><VanButton
                  plain
                  native-type="button"
                  :disabled="loading"
                  @click="loadVersions"
                  >刷新</VanButton
                >
              </div>
              <span v-else>{{ selectedSkill.node }}节点使用</span>
            </div>
            <nav class="studio-tabs" aria-label="技能工作界面">
              <button
                v-for="tab in studioTabs"
                :key="tab.id"
                type="button"
                :aria-pressed="studioTabIsActive(tab.id)"
                :class="{ selected: studioTabIsActive(tab.id) }"
                @click="changeTab(tab.id)"
              >
                {{ tab.label }}
              </button>
            </nav>
          </div>
          <div
            ref="workBody"
            class="studio-work-body"
            role="region"
            :aria-label="`${selectedSkill.name}工作内容`"
            tabindex="0"
          >
            <section
              v-if="activeAdminTab === 'overview'"
              class="skill-overview"
            >
              <p class="studio-intro">
                这里维护工作台各步骤的 AI 思路与参考示例。报告分析和日历生成仍在各自完整流程中运行。
              </p>
              <dl class="skill-usage">
                <div>
                  <dt>使用位置</dt>
                  <dd>{{ selectedSkill.node }}</dd>
                </div>
                <div>
                  <dt>输入资料</dt>
                  <dd>{{ selectedSkill.input }}</dd>
                </div>
                <div>
                  <dt>技能产出</dt>
                  <dd>{{ selectedSkill.output }}</dd>
                </div>
                <div>
                  <dt>咨询师负责</dt>
                  <dd>{{ selectedSkill.task }}</dd>
                </div>
              </dl>
              <div class="studio-entry-actions">
                <VanButton
                  plain
                  native-type="button"
                  @click="changeTab('examples')"
                  >查看参考示例</VanButton
                ><VanButton
                  plain
                  native-type="button"
                  @click="changeTab('runs')"
                  >查看运行记录</VanButton
                ><VanButton
                  v-if="isAdmin"
                  plain
                  native-type="button"
                  @click="changeTab('skills')"
                  >维护技能方法</VanButton
                >
              </div>
              <p v-if="!isAdmin">
                咨询师可查看已发布示例，并从本报告的运行结果推荐经验；管理员负责脱敏审核、版本维护和发布。
              </p>
              <p v-else-if="!isReasoningGuidanceAdmin">
                管理员可查看报告节点反馈，也可从报告或日历运行记录载入真实输入；用草稿预览和评估后再发布技能版本。
              </p>
              <details v-if="!isReasoningGuidanceAdmin">
                <summary>技术标识</summary>
                <code>{{ selectedSkill.key }}</code>
              </details>
            </section>
            <template v-else-if="activeAdminTab === 'skills' && isAdmin">
              <div class="panel-heading">
                <h3 v-if="!isReasoningGuidanceAdmin">技能维护</h3>
                <VanButton
                  class="primary-button compact-button"
                  type="primary"
                  native-type="button"
                  :disabled="saving || !selectedVersion"
                  :loading="saving"
                  @click="createDraft"
                  >{{ isReasoningGuidanceAdmin ? "创建思路草稿" : "从当前版本创建草稿" }}</VanButton
                >
              </div>
              <SkillInstructions
                v-if="selectedVersion"
                v-model:text="specificationText"
                v-model:guidance="reasoningGuidance"
                :editable="editable"
                :intent-only="isReasoningGuidanceAdmin"
                :error="specError"
                ><VanButton
                  v-if="editable"
                  plain
                  native-type="button"
                  :disabled="saving || Boolean(specError)"
                  :loading="saving"
                  @click="saveDraft"
                  >保存草稿</VanButton
                ><VanButton
                  v-if="editable"
                  type="primary"
                  native-type="button"
                  :disabled="saving || publishing || Boolean(specError)"
                  :loading="publishing"
                  @click="publish"
                  >发布版本</VanButton
                ></SkillInstructions
              >
              <p v-else>当前技能暂无可维护的版本。</p>
            </template>
            <template v-else-if="activeAdminTab === 'examples'">
              <nav
                v-if="isReasoningGuidanceAdmin"
                class="studio-tabs studio-subtabs"
                aria-label="参考与运行记录"
              >
                <button type="button" :class="{ selected: activeAdminTab === 'examples' }" @click="changeTab('examples')">示例</button>
                <button type="button" :class="{ selected: activeAdminTab === 'runs' }" @click="changeTab('runs')">运行记录</button>
                <button v-if="!isCalendarSkillAdmin" type="button" :class="{ selected: activeAdminTab === 'feedback' }" @click="changeTab('feedback')">咨询师反馈</button>
              </nav>
              <section class="examples-workspace">
                <ExamplesPanel
                  :key="selectedSkillKey"
                  :admin="isAdmin"
                  :skill-key="selectedSkillKey"
                />
              </section>
            </template>
            <section
              v-else-if="activeAdminTab === 'debug' && isAdmin"
              class="studio-run-panel"
            >
              <template v-if="isReasoningGuidanceAdmin">
                <h3>试用与质量评估</h3>
                <p v-if="isS1Admin">
                  选择程序维护的固定案例，检查草稿的依据和安全边界。评估结果供质量参考，不阻止发布。
                </p>
                <p v-else-if="isCalendarSkillAdmin">
                  使用系统维护的合成日历样本检查思路效果。评估结果供质量参考，不阻止发布；日历生成仍由原有流程负责。
                </p>
                <p v-else>
                  选择与本技能相关的固定案例，检查分析依据、解释边界和框架覆盖。评估结果供质量参考，不阻止发布。
                </p>
                <EvaluationPanel
                  :version="selectedVersion"
                  :start-evaluation="startEvaluation"
                  :require-full-dataset="isS1Admin"
                />
              </template>
              <template v-else>
                <h3>试运行技能</h3>
                <p>
                  试运行只用于验证草稿效果，不会写入报告或日历。发布技能版本前请先完成质量评估。
                </p>
                <div v-if="inputPreviewSourceRun" class="feedback-preview-source">
                  <strong>实际输入来源：{{ feedbackTargetLabel(inputPreviewSourceRun) }} · 运行 {{ inputPreviewSourceRun.id }}</strong>
                  <p v-if="feedbackSourceRun"><b>咨询师反馈</b>：{{ feedbackSourceRun.runtime_instruction || "本次运行没有补充反馈。" }}</p>
                  <p>输入框已载入该次运行的实际资料；试运行只生成预览，不会改写报告或已交付日历。</p>
                  <details>
                    <summary>查看来源运行的 AI 结果</summary>
                    <RunDetail
                      :run="inputPreviewSourceRun"
                      :admin="true"
                      :case-id="inputPreviewSourceRun.report_case_id"
                      @preview-input="prepareRunInputPreview"
                    />
                  </details>
                  <VanButton
                    v-if="feedbackSourceRun && !editable"
                    plain
                    native-type="button"
                    :disabled="saving || !selectedVersion"
                    :loading="saving"
                    @click="prepareFeedbackPreview()"
                    >基于此反馈创建可编辑草稿</VanButton
                  >
                </div>
                <label class="json-label" for="skill-input"
                  >测试输入资料（结构化数据）</label
                ><textarea
                  id="skill-input"
                  v-model="inputText"
                  class="json-editor input-editor"
                  spellcheck="false"
                ></textarea>
                <label class="json-label" for="skill-instruction"
                  >本次补充要求</label
                ><textarea
                  id="skill-instruction"
                  v-model.trim="runtimeInstruction"
                  class="instruction-input"
                  maxlength="4000"
                  rows="3"
                  placeholder="可留空"
                ></textarea>
                <p v-if="inputError" class="field-error" role="alert">
                  {{ inputError }}
                </p>
                <VanButton
                  class="primary-button"
                  type="primary"
                  native-type="button"
                  :disabled="
                    running ||
                    !selectedVersion ||
                    selectedVersion.status === 'RETIRED' ||
                    Boolean(inputError)
                  "
                  :loading="running"
                  @click="startRun"
                  >{{ running ? "正在提交" : editable ? "保存并预览草稿" : "试运行当前版本" }}</VanButton
                >
                <RunDetail
                  v-if="previewRun"
                  :key="previewRun.id"
                  class="feedback-preview-result"
                  :run="previewRun"
                  :admin="true"
                  :case-id="feedbackSourceRun?.report_case_id"
                  @preview-input="prepareRunInputPreview"
                />
              </template>
            </section>
            <EvaluationPanel
              v-else-if="activeAdminTab === 'evaluation' && isAdmin"
              :version="selectedVersion"
              :start-evaluation="startEvaluation"
            />
            <section v-else-if="activeAdminTab === 'runs'" class="runs-section">
              <nav
                v-if="isReasoningGuidanceAdmin && !isCalendarSkillAdmin"
                class="studio-tabs studio-subtabs"
                aria-label="参考与运行记录"
              >
                <button type="button" :class="{ selected: activeAdminTab === 'examples' }" @click="changeTab('examples')">示例</button>
                <button type="button" :class="{ selected: activeAdminTab === 'runs' }" @click="changeTab('runs')">运行记录</button>
                <button type="button" :class="{ selected: activeAdminTab === 'feedback' }" @click="changeTab('feedback')">咨询师反馈</button>
              </nav>
              <details
                v-if="!isAdmin"
                :open="!caseId"
                class="consultant-case-lookup"
              >
                <summary>
                  {{
                    caseId
                      ? `当前报告案例 ${caseId} · 切换报告`
                      : "选择已分配的报告案例"
                  }}
                </summary>
                <form @submit.prevent="loadCaseRuns">
                  <label for="case-id">报告案例编号</label
                  ><input
                    id="case-id"
                    v-model.trim="caseIdDraft"
                    type="number"
                    min="1"
                    required
                  /><VanButton
                    type="primary"
                    native-type="submit"
                    :disabled="caseLoading"
                    :loading="caseLoading"
                    >读取记录</VanButton
                  >
                </form>
              </details>
              <div class="panel-heading">
                <h3>本技能运行记录</h3>
                <span>{{ visibleRuns.length }} 条</span>
              </div>
              <label class="run-selector"
                >选择运行记录<select
                  :value="selectedRun?.id || ''"
                  @change="selectRunById($event.target.value)"
                >
                  <option v-if="!selectedRun" value="">选择一条记录</option>
                  <option
                    v-for="run in visibleRuns"
                    :key="run.id"
                    :value="run.id"
                  >
                    记录 {{ run.id }} ·
                    {{ RUN_STATUS_LABELS[run.status] || "未知状态" }} ·
                    {{ formatDateTime(run.created_at) }}
                  </option>
                </select></label
              >
              <RunDetail
                v-if="selectedRun"
                :key="selectedRun.id"
                :run="selectedRun"
                :admin="isAdmin"
                :allow-input-preview="!isS1Admin"
                :case-id="caseId"
                @preview-input="prepareRunInputPreview"
              />
              <p v-else>
                {{
                  isAdmin
                    ? "该版本暂无运行记录。"
                    : caseId
                      ? "本报告暂无该技能的运行记录，请回到对应节点处理。"
                      : "先选择已分配的报告，再查看运行结果和推荐经验。"
                }}
              </p>
            </section>
            <section
              v-else-if="activeAdminTab === 'feedback' && isAdmin"
              class="skill-feedback-inbox"
            >
              <nav
                v-if="isReasoningGuidanceAdmin && !isCalendarSkillAdmin"
                class="studio-tabs studio-subtabs"
                aria-label="参考与运行记录"
              >
                <button type="button" :class="{ selected: activeAdminTab === 'examples' }" @click="changeTab('examples')">示例</button>
                <button type="button" :class="{ selected: activeAdminTab === 'runs' }" @click="changeTab('runs')">运行记录</button>
                <button type="button" :class="{ selected: activeAdminTab === 'feedback' }" @click="changeTab('feedback')">咨询师反馈</button>
              </nav>
              <div class="panel-heading">
                <div>
                  <h3>咨询师反馈</h3>
                  <p v-if="isS1Admin">反馈用于发现改进方向；S1 试用统一使用系统维护的固定案例。</p>
                  <p v-else>反馈与报告案例、节点、技能版本和原始运行记录绑定，可在草稿上用该次真实输入复现。</p>
                </div>
                <span>{{ feedbackRuns.length }} 条</span>
              </div>
              <article v-for="run in feedbackRuns" :key="run.id" class="skill-feedback-card">
                <header>
                  <strong>案例 {{ run.report_case_id }} · {{ feedbackTargetLabel(run) }} · 运行 {{ run.id }}</strong>
                  <small>{{ RUN_STATUS_LABELS[run.status] || run.status }} · {{ formatDateTime(run.created_at) }}</small>
                </header>
                <p class="skill-feedback-text">{{ run.runtime_instruction }}</p>
                <div class="feedback-card-actions">
                  <VanButton
                    v-if="!isS1Admin"
                    class="primary-button compact-button"
                    type="primary"
                    native-type="button"
                    :disabled="saving || !run.input_snapshot"
                    :loading="saving && feedbackSourceRun?.id === run.id"
                    @click="prepareFeedbackPreview(run)"
                    >{{ selectedVersion?.status === 'DRAFT' ? '加载真实输入并编辑草稿' : '从反馈创建草稿并载入真实输入' }}</VanButton
                  >
                </div>
                <details class="feedback-run-details">
                  <summary>查看原始 AI 结果与节点实际输入</summary>
                  <RunDetail
                    :run="run"
                    :admin="true"
                    :allow-input-preview="!isS1Admin"
                    :case-id="run.report_case_id"
                    @preview-input="prepareRunInputPreview"
                  />
                  <details>
                    <summary>查看送入节点技能的输入快照</summary>
                    <pre class="output-block">{{ JSON.stringify(run.input_snapshot, null, 2) }}</pre>
                  </details>
                </details>
              </article>
              <p v-if="!feedbackRuns.length" class="empty-reference">
                当前技能版本还没有咨询师反馈。请在节点工作台中提交反馈并重跑后，这里会出现可复现的记录。
              </p>
            </section>
          </div>
        </section>
      </div>
    </main>
    </div>
  </div>
</template>

<script src="./studio-workspace.js"></script>

<style scoped src="./studio.css"></style>
