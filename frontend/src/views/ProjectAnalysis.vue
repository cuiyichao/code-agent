<template>
  <div class="project-analysis-container">
    <el-card class="analysis-card">
      <div slot="header" class="card-header">
        <h2>{{ currentProject ? currentProject.name : '项目分析' }}</h2>
        <el-button v-if="currentProject" @click="goBack" size="small" icon="ArrowLeft">返回列表</el-button>
      </div>

      <div v-if="loading" class="loading-container">
        <el-spinner size="large" />
        <p>正在分析项目数据...</p>
      </div>

      <div v-if="error" class="error-container">
        <el-alert :title="error" type="error" show-icon />
      </div>

      <div v-if="!loading && !error && analysisResults" class="analysis-content">
        <!-- 代码统计概览 -->
        <div class="stats-overview">
          <h3>代码统计概览</h3>
          <div class="stats-grid">
            <el-statistic :value="analysisResults.totalFiles" label="文件总数" />
            <el-statistic :value="analysisResults.totalLines" label="总行数" />
            <el-statistic :value="analysisResults.codeLines" label="代码行数" />
            <el-statistic :value="analysisResults.commentLines" label="注释行数" />
            <el-statistic :value="analysisResults.emptyLines" label="空行数" />
            <el-statistic :value="analysisResults.complexityScore" label="复杂度分数" />
          </div>
        </div>

        <!-- 文件类型分布 -->
        <div class="chart-container">
          <h3>文件类型分布</h3>
          <v-chart :option="fileTypeOption" height="300px" />
        </div>

        <!-- 代码复杂度趋势 -->
        <div class="chart-container">
          <h3>代码复杂度趋势</h3>
          <v-chart :option="complexityTrendOption" height="300px" />
        </div>

        <!-- 符号分析表格 -->
        <div class="symbols-table">
          <h3>代码符号分析</h3>
          <el-table :data="analysisResults.symbols" stripe border>
            <el-table-column prop="name" label="符号名称" />
            <el-table-column prop="type" label="类型" />
            <el-table-column prop="file" label="文件路径" />
            <el-table-column prop="line" label="行号" />
            <el-table-column prop="complexity" label="复杂度" />
          </el-table>
        </div>

        <!-- 语义变更分析 -->
        <div class="changes-analysis">
          <h3>语义变更分析</h3>
          <el-timeline>
            <el-timeline-item
              v-for="(change, index) in analysisResults.semanticChanges"
              :key="index"
              :timestamp="change.timestamp"
            >
              <el-card>
                <h4>{{ change.type }}: {{ change.description }}</h4>
                <p>影响范围: {{ change.impact }}</p>
                <div v-if="change.codeSnippet" class="code-snippet">
                  <highlightjs language="javascript" :code="change.codeSnippet" />
                </div>
                <div class="change-actions" style="margin-top: 10px;">
                  <el-button size="small" @click="selectedFile = change.fileDiff">查看代码差异</el-button>
                  <el-button size="small" type="primary" @click="() => { currentTestCase = change.testCase; showTestCodeDialog = true; }">查看测试用例</el-button>
                </div>
              </el-card>
            </el-timeline-item>
          </el-timeline>
        </div>

        <!-- 代码差异显示 -->
        <div v-if="selectedFile" class="code-diff-section">
          <h3>代码差异对比</h3>
          <DiffEditor
            :original-code="selectedFile.oldContent"
            :modified-code="selectedFile.newContent"
            :language="getFileLanguage(selectedFile.path)"
            :file-path="selectedFile.path"
            :additions="selectedFile.additions"
            :deletions="selectedFile.deletions"
            :height="'500px'"
          />
        </div>

        <!-- 测试代码对话框 -->
        <TestCodeDialog
          v-model="showTestCodeDialog"
          :test-case="currentTestCase"
          :editable="true"
          @save="saveTestCase"
          @run="runTestCase"
        />
      </div>
    </el-card>
  </div>
</template>

<script>
import { ref, onMounted, computed } from 'vue';
import { useStore } from 'vuex';
import { useRoute, useRouter } from 'vue-router';
import { getProjectAnalysis } from '@/services/api';
import { VChart } from 'vue-echarts';
import 'echarts/lib/chart/pie';
import 'echarts/lib/chart/line';
import 'echarts/lib/component/tooltip';
import 'echarts/lib/component/legend';
import hljs from 'highlight.js';
import 'highlight.js/styles/github.css';
import DiffEditor from '@/components/DiffEditor.vue';
import TestCodeDialog from '@/components/TestCodeDialog.vue';
import { ref } from 'vue';

export default {
  name: 'ProjectAnalysis',
  components: {
    VChart,
    DiffEditor,
    TestCodeDialog
  },
  setup() {
    const store = useStore();
    const route = useRoute();
    const router = useRouter();
    const loading = ref(true);
    const error = ref(null);
    const projectId = route.params.id;

    // 从Vuex获取当前项目和分析结果
    const currentProject = computed(() => store.state.currentProject);
    const analysisResults = computed(() => store.state.analysisResults);

    // 图表配置
    const fileTypeOption = ref({
      tooltip: { trigger: 'item' },
      legend: { position: 'right' },
      series: [
        {
          name: '文件类型',
          type: 'pie',
          radius: ['40%', '70%'],
          avoidLabelOverlap: false,
          itemStyle: {
            borderRadius: 10,
            borderColor: '#fff',
            borderWidth: 2,
          },
          label: { show: false, position: 'center' },
          emphasis: { label: { show: true, fontSize: 16 } },
          labelLine: { show: false },
          data: [],
        },
      ],
    });

    const complexityTrendOption = ref({
      tooltip: { trigger: 'axis' },
      legend: { data: ['复杂度'] },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'category', boundaryGap: false, data: [] },
      yAxis: { type: 'value' },
      series: [
        {
          name: '复杂度',
          type: 'line',
          stack: 'Total',
          data: [],
        },
      ],
    });

    // 获取项目分析数据
    const fetchProjectAnalysis = async () => {
      try {
        loading.value = true;
        const data = await getProjectAnalysis(projectId);
        store.commit('setAnalysisResults', data);
        updateCharts(data);
      } catch (err) {
        error.value = '获取项目分析数据失败: ' + (err.message || '未知错误');
        console.error('Analysis fetch error:', err);
      } finally {
        loading.value = false;
      }
    };

    // 更新图表数据
    const updateCharts = (data) => {
      // 文件类型分布
      fileTypeOption.value.series[0].data = data.fileTypeDistribution || [];

      // 复杂度趋势
      complexityTrendOption.value.xAxis.data = data.complexityTrend?.dates || [];
      complexityTrendOption.value.series[0].data = data.complexityTrend?.scores || [];
    };

    // 返回项目列表
    const goBack = () => {
      router.push('/projects');
    };

    onMounted(() => {
      // 如果Vuex中没有当前项目，从URL参数获取
      if (!currentProject.value && projectId) {
        const project = store.state.projects.find(p => p.id === projectId);
        if (project) {
          store.commit('setCurrentProject', project);
        }
      }
      fetchProjectAnalysis();
    });

    const getFileLanguage = (filePath) => {
  if (!filePath) return 'javascript';
  const ext = filePath.split('.').pop().toLowerCase();
  const langMap = {
    'js': 'javascript',
    'ts': 'typescript',
    'vue': 'vue',
    'html': 'html',
    'css': 'css',
    'scss': 'scss',
    'json': 'json',
    'py': 'python',
    'java': 'java',
    'cpp': 'cpp',
    'c': 'c',
    'go': 'go',
    'rb': 'ruby',
    'php': 'php'
  };
  return langMap[ext] || 'javascript';
};

const saveTestCase = (updatedTestCase) => {
  // 实现保存测试用例的逻辑
  console.log('保存测试用例:', updatedTestCase);
  // 可以在这里调用API保存修改
};

const runTestCase = async (testCase) => {
  // 实现运行测试用例的逻辑
  console.log('运行测试用例:', testCase);
  // 模拟测试运行
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve({
        status: 'success',
        output: '测试通过:\n\n✓ 测试用例执行成功\n✓ 断言全部通过\n\n执行时间: 127ms'
      });
    }, 1500);
  });
};

return {
  currentProject,
  analysisResults,
  loading,
  error,
  fileTypeOption,
  complexityTrendOption,
  goBack,
  selectedFile,
  showTestCodeDialog,
  currentTestCase,
  getFileLanguage,
  saveTestCase,
  runTestCase
};
  },
};
</script>

<style scoped>
.project-analysis-container {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.loading-container {
  text-align: center;
  padding: 50px 0;
}

.error-container {
  margin: 20px 0;
}

.analysis-content {
  display: flex;
  flex-direction: column;
  gap: 30px;
}

.stats-overview {
  margin-bottom: 20px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
  margin-top: 16px;
}

.chart-container {
  width: 100%;
  margin: 16px 0;
}

.symbols-table {
  margin: 16px 0;
}

.changes-analysis {
  margin: 16px 0;
}

.code-snippet {
  margin-top: 10px;
  background-color: #f5f5f5;
  padding: 10px;
  border-radius: 4px;
  overflow-x: auto;
}
</style>