<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useFiltersStore } from '@/stores/filters'
import { spotsApi } from '@/api/spots'
import type { SpotBrief } from '@/api/types'
import { formatInt, pickTierColor } from '@/utils/format'
import { useRouter } from 'vue-router'

const router = useRouter()
const filters = useFiltersStore()
const list = ref<SpotBrief[]>([])
const total = ref(0)
const cities = ref<Array<{ city: string; spot_count: number }>>([])
const loading = ref(false)

async function loadCities() {
  cities.value = await spotsApi.cities()
}
async function loadList() {
  loading.value = true
  try {
    const page = await spotsApi.list(filters.filter)
    list.value = page.items
    total.value = page.total
  } finally {
    loading.value = false
  }
}

function applyFilter() {
  filters.update({ page: 1 })
  loadList()
}

function resetAll() {
  filters.reset()
  loadList()
}

onMounted(() => {
  loadCities()
  loadList()
})

watch(() => filters.filter.page, loadList)
</script>

<template>
  <div class="explore-root">
    <aside class="filter-panel">
      <h3>筛选条件</h3>

      <el-form :model="filters.filter" label-position="top" size="large">
        <el-form-item label="城市">
          <el-select v-model="filters.filter.city" clearable placeholder="全部" filterable>
            <el-option
              v-for="c in cities" :key="c.city"
              :label="`${c.city} (${c.spot_count})`" :value="c.city"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="等级">
          <el-radio-group v-model="filters.filter.level">
            <el-radio-button :label="undefined">全部</el-radio-button>
            <el-radio-button label="5A" />
            <el-radio-button label="4A" />
            <el-radio-button label="3A" />
          </el-radio-group>
        </el-form-item>

        <el-form-item label="评论档位">
          <el-radio-group v-model="filters.filter.tier">
            <el-radio-button :label="undefined">全部</el-radio-button>
            <el-radio-button label="high">高</el-radio-button>
            <el-radio-button label="medium">中</el-radio-button>
            <el-radio-button label="low">少</el-radio-button>
            <el-radio-button label="silent">无</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="最低评分">
          <el-slider
            v-model="filters.filter.min_grade"
            :min="0" :max="5" :step="0.1"
            show-tooltip
          />
        </el-form-item>

        <div class="actions">
          <el-button type="primary" size="large" @click="applyFilter">应用</el-button>
          <el-button size="large" @click="resetAll">重置</el-button>
        </div>
      </el-form>
    </aside>

    <section class="result">
      <header class="result-header">
        <span>共 <b>{{ formatInt(total) }}</b> 条结果，当前第 {{ filters.filter.page ?? 1 }} 页</span>
        <el-pagination
          v-model:current-page="filters.filter.page"
          :page-size="filters.filter.page_size ?? 30"
          :total="total"
          :pager-count="9"
          layout="prev, pager, next, jumper"
          background
        />
      </header>

      <el-table :data="list" v-loading="loading" stripe size="large"
                :default-sort="{ prop: 'comment_count_real', order: 'descending' }">
        <el-table-column prop="name" label="景区" min-width="200">
          <template #default="{ row }">
            <a class="link" @click="router.push(`/spot/${row.id}`)">{{ row.name }}</a>
          </template>
        </el-table-column>
        <el-table-column prop="city" label="城市" width="130" />
        <el-table-column prop="level" label="等级" width="90">
          <template #default="{ row }">
            <el-tag v-if="row.level" type="warning" size="default">{{ row.level }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="grade" label="评分" width="90" sortable />
        <el-table-column prop="hot" label="热度" width="90" sortable />
        <el-table-column prop="comment_count_real" label="真实评论" width="130" sortable>
          <template #default="{ row }">{{ formatInt(row.comment_count_real) }}</template>
        </el-table-column>
        <el-table-column prop="comment_tier" label="档位" width="110">
          <template #default="{ row }">
            <el-tag :color="pickTierColor(row.comment_tier)" effect="dark" size="default">
              {{ row.comment_tier ?? '-' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </section>
  </div>
</template>

<style scoped>
/* perf #12: 字号整体上调到 17px (浏览器默认 16px 之上), 配合 size="large" 让表格/筛选清晰可读 */
.explore-root {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 18px;
  padding: 18px 28px;
  font-size: 17px;
}
.filter-panel { background: #fff; border-radius: 10px; padding: 20px 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); height: fit-content; }
.filter-panel h3 { margin: 0 0 16px; font-size: 20px; font-weight: 600; }
.actions { display: flex; gap: 12px; margin-top: 12px; }
.result { background: #fff; border-radius: 10px; padding: 20px 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
.result-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 14px;
  color: #475569;
  font-size: 15px;
}
.result-header b { color: #1e293b; font-weight: 600; font-size: 16px; }
.link { color: #2563eb; cursor: pointer; font-weight: 500; }
.link:hover { text-decoration: underline; }

/* el-table 字号不受 size 控制, 通过 :deep() 穿透 */
.result :deep(.el-table) { font-size: 16px; }
.result :deep(.el-table th .cell) { font-size: 15px; font-weight: 600; }
.result :deep(.el-form-item__label) { font-size: 16px; font-weight: 500; }

@media (max-width: 900px) {
  .explore-root { grid-template-columns: 1fr; }
}
</style>
