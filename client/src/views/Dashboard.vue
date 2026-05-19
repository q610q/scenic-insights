<script setup lang="ts">
import { onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useDashboardStore } from '@/stores/dashboard'

import KpiCard       from '@/components/charts/KpiCard.vue'
import ChinaMap      from '@/components/charts/ChinaMap.vue'
import TopSpotsBar   from '@/components/charts/TopSpotsBar.vue'
import LevelPie      from '@/components/charts/LevelPie.vue'
import ScatterHotGrade from '@/components/charts/ScatterHotGrade.vue'
import WordCloud     from '@/components/charts/WordCloud.vue'

const store = useDashboardStore()
const { globalKpi, topSpots, heatmap, levelDist, wordcloud, loading, error } = storeToRefs(store)

onMounted(() => store.loadAll())
</script>

<template>
  <div class="dashboard-root">
    <header class="dash-header">
      <h1>
        <span class="dash-emoji">🗺</span>
        旅游数据可视化大屏
      </h1>
      <div class="dash-meta">
        <el-tag v-if="loading" type="info" size="small">加载中…</el-tag>
        <el-tag v-else-if="error" type="danger" size="small">{{ error }}</el-tag>
        <el-tag v-else type="success" size="small">数据已加载</el-tag>
        <router-link to="/explore" class="link">筛选探索 →</router-link>
      </div>
    </header>

    <section class="kpi-row">
      <KpiCard label="景区总数"   :value="globalKpi?.spot_total ?? 0"        icon="🏞" accent="#10b981" />
      <KpiCard label="真实评论"   :value="globalKpi?.real_comment_total ?? 0" icon="💬" accent="#3b82f6" />
      <KpiCard label="平均评分"   :value="globalKpi?.avg_grade ?? '-'"        icon="⭐" accent="#f59e0b" unit="/ 5" />
      <KpiCard label="覆盖城市"   :value="globalKpi?.city_count ?? 0"         icon="🌆" accent="#a855f7" />
    </section>

    <section class="row-2">
      <article class="panel panel-lg">
        <h3>🗺 全国景区分布 / 评论热力</h3>
        <ChinaMap :data="heatmap" height="500px" />
      </article>
      <article class="panel">
        <h3>🎯 景区等级分布</h3>
        <LevelPie :data="levelDist" height="500px" />
      </article>
    </section>

    <section class="row-3">
      <article class="panel">
        <h3>🏆 Top 10 评论数景区</h3>
        <TopSpotsBar :data="topSpots" height="420px" />
      </article>
      <article class="panel">
        <h3>💎 评分 × 热度散点</h3>
        <ScatterHotGrade :data="topSpots" height="420px" />
      </article>
    </section>

    <section class="row-4">
      <article class="panel">
        <h3>☁ 评论关键词云</h3>
        <WordCloud :words="wordcloud" height="360px" />
      </article>
    </section>

    <footer class="dash-footer">
      数据来源：data/ ETL 流水线 / FastAPI · {{ new Date().toLocaleString('zh-CN') }}
    </footer>
  </div>
</template>

<style scoped>
.dashboard-root {
  min-height: 100vh;
  background: linear-gradient(135deg, #0a0e1a 0%, #0f172a 100%);
  color: var(--dash-text);
  padding: 24px 32px 16px;
  display: flex; flex-direction: column; gap: 20px;
}
.dash-header { display: flex; justify-content: space-between; align-items: center; }
.dash-header h1 {
  margin: 0; font-size: 26px; font-weight: 700;
  color: var(--dash-text-strong);
  background: linear-gradient(90deg, #818cf8, #c084fc, #f0abfc);
  -webkit-background-clip: text; background-clip: text;
  -webkit-text-fill-color: transparent;
}
.dash-emoji { -webkit-text-fill-color: initial; margin-right: 8px; }
.dash-meta { display: flex; gap: 12px; align-items: center; }
.dash-meta .link { color: var(--dash-accent); font-size: 13px; }

.kpi-row {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px;
}
.row-2 {
  display: grid; grid-template-columns: 2fr 1fr; gap: 16px;
}
.row-3 {
  display: grid; grid-template-columns: 1fr 1fr; gap: 16px;
}

.panel {
  background: var(--dash-card-bg);
  border: 1px solid var(--dash-border);
  border-radius: 12px;
  padding: 16px 20px;
  box-shadow: 0 4px 14px rgba(0,0,0,0.18);
  /* perf #8: contain 圈定 panel 重绘范围，滚动时浏览器只 paint 进入视口的 panel */
  contain: layout paint style;
}
.panel h3 {
  margin: 0 0 12px;
  font-size: 14px; font-weight: 600;
  color: var(--dash-text-strong);
  letter-spacing: 0.02em;
}
.panel-lg {
  min-height: 540px;
  /* perf #9: 强制 GPU 合成层不释放, 避免 ChinaMap 滚出视口后第一帧重新光栅化卡顿 */
  will-change: transform;
  transform: translateZ(0);
}

.dash-footer {
  text-align: right;
  font-size: 12px;
  color: var(--dash-text);
  padding: 8px 4px;
  opacity: 0.7;
}

@media (max-width: 1100px) {
  .row-2 { grid-template-columns: 1fr; }
  .row-3 { grid-template-columns: 1fr; }
  .kpi-row { grid-template-columns: repeat(2, 1fr); }
}
</style>
