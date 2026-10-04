<template>
  <div class="skill-studio-shell">
    <main class="skill-studio-main">
      <header class="studio-heading">
        <router-link
          class="secondary-button compact-button"
          :to="studioReturnLocation"
          >返回咨询工作台</router-link
        >
        <h1>技能与示例工作台</h1>
        <span>{{ isAdmin ? "管理员维护" : "咨询师参考" }}</span>
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
        <aside class="skill-catalog" aria-label="咨询流程技能">
          <h2>咨询流程技能</h2>
          <p>按报告节点维护方法与示例</p>
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
                :aria-pressed="activeAdminTab === tab.id"
                :class="{ selected: activeAdminTab === tab.id }"
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
                这里维护咨询工作台使用的技能方法和参考示例。分析、审核和报告交付在对应报告节点中完成。
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
              <details>
                <summary>技术标识</summary>
                <code>{{ selectedSkill.key }}</code>
              </details>
            </section>
            <template v-else-if="activeAdminTab === 'skills' && isAdmin">
              <div class="panel-heading">
                <h3>技能维护</h3>
                <VanButton
                  class="primary-button compact-button"
                  type="primary"
                  native-type="button"
                  :disabled="saving || !selectedVersion"
                  :loading="saving"
                  @click="createDraft"
                  >从当前版本创建草稿</VanButton
                >
              </div>
              <SkillInstructions
                v-if="selectedVersion"
                v-model:text="specificationText"
                :editable="editable"
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
            <ExamplesPanel
              v-else-if="activeAdminTab === 'examples'"
              :key="selectedSkillKey"
              :admin="isAdmin"
              :skill-key="selectedSkillKey"
            />
            <section
              v-else-if="activeAdminTab === 'debug' && isAdmin"
              class="studio-run-panel"
            >
              <h3>试运行技能</h3>
              <p>
                验证当前版本的输出。试运行结果须经过咨询师审核，才能用于实际报告。
              </p>
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
                >{{ running ? "正在提交" : "开始试运行" }}</VanButton
              >
            </section>
            <EvaluationPanel
              v-else-if="activeAdminTab === 'evaluation' && isAdmin"
              :version="selectedVersion"
              :start-evaluation="startEvaluation"
            />
            <section v-else-if="activeAdminTab === 'runs'" class="runs-section">
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
                    {{ formatDate(run.created_at) }}
                  </option>
                </select></label
              >
              <RunDetail
                v-if="selectedRun"
                :key="selectedRun.id"
                :run="selectedRun"
                :admin="isAdmin"
                :case-id="caseId"
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
          </div>
        </section>
      </div>
    </main>
  </div>
</template>

<script src="./studio-workspace.js"></script>

<style scoped src="./studio.css"></style>
