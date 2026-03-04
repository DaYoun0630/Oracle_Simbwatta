<script setup>
import AppShell from "../components/AppShell.vue";
</script>

<template>
  <AppShell title="정밀 인지 분석" :showBack="true">
    <section class="analysis-grid">
      <div class="card diagnosis-card">
        <h3>모델 판별 결과</h3>
        <div class="probability-bar">
          <div class="label">EMCI 의심 확률</div>
          <div class="bar-bg"><div class="bar-fill" :style="{ width: '35%' }"></div></div>
          <span class="value">35.2%</span>
        </div>
      </div>

      <div class="card feature-card">
        <h3>추출 특징 분석 (Acoustic/Linguistic)</h3>
        <table class="data-table">
          <thead>
            <tr>
              <th>지표</th>
              <th>현재값</th>
              <th>기준점</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>발화 속도(VAD)</td>
              <td>1.2 words/s</td>
              <td>1.5 words/s</td>
            </tr>
            <tr>
              <td>명사 사용 비율</td>
              <td>22%</td>
              <td>30%</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </AppShell>
</template>

<style scoped>
.analysis-grid { display: grid; gap: 16px; }
.card { background: #fff; padding: 20px; border-radius: 20px; box-shadow: 8px 8px 16px #d1d9e6, -8px -8px 16px #ffffff; }
.probability-bar { margin-top: 12px; }
.bar-bg { background: #e0e5ec; height: 12px; border-radius: 6px; overflow: hidden; margin: 4px 0; }
.bar-fill { background: #4cb7b7; height: 100%; transition: width 1s ease-out; }
.data-table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px; }
.data-table th { text-align: left; color: #888; padding-bottom: 8px; }
.data-table td { padding: 8px 0; border-top: 1px solid #f0f0f0; }
</style>