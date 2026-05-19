<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { spotsApi } from '@/api/spots'
import { commentsApi } from '@/api/comments'
import { dashboardApi } from '@/api/dashboard'
import type { CommentItem, MonthlyTrend, SpotDetail } from '@/api/types'
import MonthlyLine     from '@/components/charts/MonthlyLine.vue'
import GradeRatingPie  from '@/components/charts/GradeRatingPie.vue'
import { shorten } from '@/utils/format'

const props = defineProps<{ id: number }>()

const detail = ref<SpotDetail | null>(null)
const monthly = ref<MonthlyTrend[]>([])
const grades = ref<Record<string, number> | null>(null)
const comments = ref<CommentItem[]>([])
const cursor = ref<number | null>(null)
const hasMore = ref(true)
const tab = ref('intro')

async function loadDetail() {
  detail.value = await spotsApi.detail(props.id)
}
async function loadCharts() {
  const [m, g] = await Promise.all([
    dashboardApi.monthlyTrend(props.id),
    spotsApi.gradeDist(props.id),
  ])
  monthly.value = m
  grades.value = g
}
async function loadComments() {
  if (!hasMore.value) return
  const page = await commentsApi.list(props.id, cursor.value, 20)
  comments.value.push(...page.items)
  cursor.value = page.next_cursor
  hasMore.value = page.has_more
}

onMounted(() => {
  loadDetail()
  loadCharts()
  loadComments()
})
watch(() => props.id, () => {
  detail.value = null
  comments.value = []
  cursor.value = null
  hasMore.value = true
  loadDetail()
  loadCharts()
  loadComments()
})

const tagColor = computed(() => {
  switch (detail.value?.level) {
    case '5A': return 'danger'
    case '4A': return 'warning'
    case '3A': return 'success'
    default:   return 'info'
  }
})
</script>

<template>
  <div class="spot-detail" v-if="detail">
    <header class="header">
      <div class="title-row">
        <h1>{{ detail.name }}</h1>
        <el-tag v-if="detail.level" :type="tagColor" size="large">{{ detail.level }}</el-tag>
        <el-tag v-if="detail.tag" type="info" size="default" effect="plain">{{ detail.tag }}</el-tag>
      </div>
      <div class="meta-row">
        <span v-if="detail.location">📍 {{ detail.location }}</span>
        <span v-if="detail.phone">☎ {{ detail.phone }}</span>
      </div>
      <div class="stats-row">
        <span class="stat"><b>{{ detail.grade ?? '-' }}</b><small>景区评分</small></span>
        <span class="stat"><b>{{ detail.hot ?? '-' }}</b><small>热度</small></span>
        <span class="stat"><b>{{ detail.comment_count_real }}</b><small>真实评论</small></span>
        <span class="stat"><b>{{ detail.total_comments_raw ?? 0 }}</b><small>原始评论数</small></span>
      </div>
    </header>

    <section class="charts-row">
      <article class="panel">
        <h3>📈 月度评论趋势</h3>
        <MonthlyLine :data="monthly" height="280px" />
      </article>
      <article class="panel">
        <h3>⭐ 评分分布</h3>
        <GradeRatingPie :spot-metric="grades" height="280px" />
      </article>
    </section>

    <section class="tabs-section">
      <el-tabs v-model="tab">
        <el-tab-pane label="景区介绍" name="intro">
          <pre class="long-text">{{ detail.intro || '暂无介绍' }}</pre>
        </el-tab-pane>
        <el-tab-pane label="入园公告" name="notice">
          <pre class="long-text">{{ detail.notice || '无' }}</pre>
        </el-tab-pane>
        <el-tab-pane label="小贴士" name="tips">
          <pre class="long-text">{{ detail.tips || '无' }}</pre>
        </el-tab-pane>
        <el-tab-pane :label="`评论 (${detail.comment_count_real})`" name="comments">
          <div v-if="!detail.has_real_comments" class="empty">该景区暂无真实评论（仅默认评）</div>
          <ul class="comment-list" v-else>
            <li v-for="c in comments" :key="c.id" class="comment-item">
              <header>
                <span class="co-name">{{ c.co_name ?? '匿名' }}</span>
                <el-rate :model-value="c.co_grade ?? 0" disabled size="small" />
                <span class="co-time">{{ c.co_time }}</span>
                <span v-if="c.ip_region" class="ip">{{ c.ip_region }}</span>
              </header>
              <p>{{ c.content }}</p>
            </li>
          </ul>
          <el-button v-if="hasMore && detail.has_real_comments" @click="loadComments" :loading="false" plain>
            加载更多
          </el-button>
        </el-tab-pane>
      </el-tabs>
    </section>
  </div>
  <div v-else class="loading">加载中...</div>
</template>

<style scoped>
.spot-detail { padding: 16px 32px; max-width: 1200px; margin: 0 auto; }
.header { background: #fff; padding: 24px 28px; border-radius: 12px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
.title-row { display: flex; gap: 12px; align-items: center; }
.title-row h1 { margin: 0; font-size: 28px; }
.meta-row { color: #64748b; font-size: 14px; margin-top: 8px; display: flex; gap: 24px; }
.stats-row { display: flex; gap: 32px; margin-top: 16px; padding-top: 16px; border-top: 1px dashed #e5e7eb; }
.stat { display: flex; flex-direction: column; }
.stat b { font-size: 22px; color: #1f2937; }
.stat small { color: #64748b; font-size: 12px; }

.charts-row { display: grid; grid-template-columns: 2fr 1fr; gap: 16px; margin-bottom: 16px; }
.panel { background: #fff; border-radius: 12px; padding: 16px 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
.panel h3 { margin: 0 0 8px; font-size: 14px; }

.tabs-section { background: #fff; border-radius: 12px; padding: 16px 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
.long-text { white-space: pre-wrap; font-family: inherit; line-height: 1.7; color: #334155; max-height: 480px; overflow-y: auto; margin: 0; }

.comment-list { list-style: none; padding: 0; margin: 0; }
.comment-item { border-bottom: 1px solid #f1f5f9; padding: 12px 0; }
.comment-item header { display: flex; gap: 12px; align-items: center; font-size: 13px; color: #64748b; }
.co-name { font-weight: 600; color: #1f2937; }
.co-time { margin-left: auto; }
.ip { font-size: 12px; }
.comment-item p { margin: 6px 0 0; line-height: 1.6; color: #1f2937; }
.empty { color: #94a3b8; padding: 32px; text-align: center; }
.loading { padding: 60px; text-align: center; color: #94a3b8; }

@media (max-width: 900px) {
  .charts-row { grid-template-columns: 1fr; }
}
</style>
