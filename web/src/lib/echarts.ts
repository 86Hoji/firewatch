// ECharts, tree-shaken, with the Black Marble look applied per chart (no default theme anywhere).
import * as echarts from 'echarts/core';
import { LineChart } from 'echarts/charts';
import { GridComponent, MarkLineComponent, TooltipComponent, AxisPointerComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';

echarts.use([LineChart, GridComponent, MarkLineComponent, TooltipComponent, AxisPointerComponent, CanvasRenderer]);

export { echarts };

export const C = {
  gold: '#F5B83D',
  goldPale: '#FFE7A3',
  ember: '#D4891C',
  text: '#EEF2FB',
  text2: '#9AA8C7',
  text3: '#5F6E91',
  map2: '#B7C2DB',
  ice: '#93C5FD',
  line: 'rgba(148,170,220,0.12)',
  font: "'Geist Variable', 'Geist', system-ui, sans-serif",
};

export const axisLabel = {
  color: C.map2,
  fontFamily: C.font,
  fontSize: 13,
};
