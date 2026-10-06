<template>
  <div class="request-form-page">
    <BrandNav />
    <main class="request-form-main">
      <BrandPageHeader class="form-hero" contained eyebrow="YOUR NEXT 30 DAYS" title="基于报告生成决策日历" description="日历只会基于已交付的人生说明书生成。请从报告详情选择这 30 天的起始日期与关注目标。" seal="知序">
        <span class="request-form-note">30 天个人日历 · 成功后自动交付</span>
      </BrandPageHeader>

      <form v-if="ready" class="request-form paper-card" novalidate @submit.prevent="submitRequest">
        <section class="form-section" aria-labelledby="profile-title">
          <div class="section-heading">
            <p class="section-kicker">01 / PROFILE SNAPSHOT</p>
            <h2 id="profile-title">确认出生资料</h2>
            <p>这份资料会随本次申请保存为快照；接单后申请资料将锁定。</p>
          </div>

          <div class="form-grid two">
            <label class="field">
              <span>姓名 <b>*</b></span>
              <input v-model.trim="form.name" type="text" autocomplete="name" maxlength="50" required>
              <small v-if="errors.name" class="field-error">{{ errors.name }}</small>
            </label>
            <fieldset class="field choice-fieldset">
              <legend>性别 <b>*</b></legend>
              <div class="choice-row">
                <VanButton type="default" native-type="button" :class="{ selected: form.gender === 'male' }" :aria-pressed="form.gender === 'male'" @click="form.gender = 'male'">男</VanButton>
                <VanButton type="default" native-type="button" :class="{ selected: form.gender === 'female' }" :aria-pressed="form.gender === 'female'" @click="form.gender = 'female'">女</VanButton>
              </div>
              <small v-if="errors.gender" class="field-error">{{ errors.gender }}</small>
            </fieldset>
          </div>

          <BirthDateField
            :profile="form"
            :errors="{ birth_date: errors.birth }"
            id-prefix="calendar-request"
            @set-birth-date="setBirthDate"
          />

          <div class="form-grid two">
            <fieldset class="field choice-fieldset">
              <legend>历法类型 <b>*</b></legend>
              <div class="choice-row"><VanButton type="default" native-type="button" :class="{ selected: form.calendar_type === 'solar' }" :aria-pressed="form.calendar_type === 'solar'" @click="selectCalendarType('solar')">公历</VanButton><VanButton type="default" native-type="button" :class="{ selected: form.calendar_type === 'lunar' }" :aria-pressed="form.calendar_type === 'lunar'" @click="selectCalendarType('lunar')">农历</VanButton></div>
            </fieldset>
            <label class="field"><span>出生地 <em>选填</em></span><input v-model.trim="form.birth_place" type="text" maxlength="100" placeholder="如：北京、上海"></label>
          </div>

          <fieldset class="field choice-fieldset">
            <legend>出生时间 <em>选填</em></legend>
            <div class="choice-row choice-row-wide"><VanButton v-for="item in timeOptions" :key="item.value" type="default" native-type="button" :class="{ selected: form.time_accuracy === item.value }" :aria-pressed="form.time_accuracy === item.value" @click="selectTimeAccuracy(item.value)">{{ item.label }}</VanButton></div>
            <div v-if="form.time_accuracy !== 'unknown'" class="time-row"><input v-model.number="form.birth_hour" type="number" min="0" max="23" placeholder="08" aria-label="出生时"><span>:</span><input v-model.number="form.birth_minute" type="number" min="0" max="59" placeholder="30" aria-label="出生分"></div>
          </fieldset>
        </section>

        <section class="form-section" aria-labelledby="calendar-title">
          <div class="section-heading"><p class="section-kicker">02 / REQUEST FOCUS</p><h2 id="calendar-title">告诉我们你想照看的节奏</h2><p>日历固定覆盖起始日期后的 30 天，将根据已交付报告和你的目标直接生成。</p></div>
          <div class="form-grid two">
            <label class="field"><span>起始日期 <b>*</b></span><input v-model="form.start_date" type="date" required><small class="field-hint">将生成 {{ dateRangeLabel }}</small><small v-if="errors.start_date" class="field-error">{{ errors.start_date }}</small></label>
            <label class="field"><span>关注目标 <b>*</b></span><input v-model.trim="form.calendar_goal" type="text" maxlength="500" placeholder="例如：安排转型、稳定作息、做重要决定" required><small v-if="errors.calendar_goal" class="field-error">{{ errors.calendar_goal }}</small></label>
          </div>
          <label class="field"><span>补充说明 <em>选填</em></span><textarea v-model.trim="form.additional_info" rows="5" maxlength="4000" placeholder="可以写下近期处境、希望被提醒的事项，或你对日历语气的期待。"></textarea><small class="field-hint">{{ form.additional_info.length }}/4000</small></label>
        </section>

        <div class="form-footer">
          <p class="privacy-note"><span aria-hidden="true">◆</span> 提交后先进入咨询师工作台，不会直接生成或展示给其他用户。</p>
          <div class="form-actions"><router-link class="secondary-button" to="/pages/requests/requests">返回我的申请</router-link><VanButton class="primary-button" type="primary" native-type="submit" :disabled="submitting" :aria-busy="submitting">{{ submitting ? '提交中…' : editing ? '更新并重新提交' : '提交日历申请' }}</VanButton></div>
          <p v-if="formMessage" class="form-error" role="alert" aria-live="assertive">{{ formMessage }}</p>
        </div>
      </form>

      <section v-else class="loading-card paper-card" role="status" aria-live="polite">正在准备申请表…</section>
    </main>
    <BrandFooter />
  </div>
</template>

<script src="../features/service-requests/request-form.js"></script>

<style scoped src="../features/service-requests/request-form.css"></style>
