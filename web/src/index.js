import 'bootstrap';
import 'bootstrap/dist/css/bootstrap.min.css';
import './custom.css'

import * as d3 from 'd3';
import embed from 'vega-embed';
import * as st from './structure_tree.js';
import * as th from './trace_heatmap.js'
import * as trace from './trace.js';
import { schemeDark2 } from 'd3';

const MAX_TRACES_TO_LOAD = 5000;

const pairUp = (arr) => {
    return arr.reduce((acc, cur) => {
        if (acc.length == 0 || acc[acc.length - 1].length == 2) {
            acc.push([cur]);
        } else {
            acc[acc.length - 1].push(cur);
        }
        return acc;
    }, [])
}

const dateFromTimestamp = (timestamp) => new Date(timestamp / 1000);

const newUi = (title) => {
    d3.select('#current-view').text(title);
    d3.select(".struct-tip").style("opacity", 0);
    const charts = d3.select('.charts');
    charts.html("");

    return charts;
}

const updateTraceChart = (traceId) => {
    d3.select('#current-view').text(`${traceId} Trace Explorer`);
    embed(
        '#trace-chart',
        `trace_chart/${traceId}`
    ).catch(console.error);
    embed(
        '#trace-tree-chart',
        `trace_tree_chart/${traceId}`,
        {width: 875}
    ).catch(console.error);
}

const traceExplorer = (traceId, traceIds) => {
    const charts = newUi(`${traceId} Trace Explorer`);

    const crow = charts
        .append('div')
        .attr('class', 'row');

    const vizCol = crow
        .append('div')
        .attr('class', 'col');
    
    vizCol.append('div')
        .attr('class', 'row')
        .append('div')
        .attr('class', 'col')
        .attr('id', 'trace-chart');
    
    vizCol.append('div')
        .attr('class', 'row')
        .append('div')
        .attr('class', 'col')
        .attr('id', 'trace-tree-chart');
    
    vizCol.append('div')
        .attr('class', 'row')
        .append('div')
        .attr('class', 'col')
        .attr('id', '#');

    const traceNavCol = crow
        .append('div')
        .attr('class', 'col col-sm')
        .attr('id', 'trace-list');

    traceNavCol.append('ul')
        .selectAll('li')
        .data(traceIds)
        .join('li')
        .append('a')
        .attr('class', 'trace-select-link')
        .text(d => d)
        .on('click', (e, i) => {
            updateTraceChart(i);
            // reset existing selected...
            d3.selectAll('.trace-select-link').attr('class', 'trace-select-link');
            d3.select(e.target).attr('class', 'trace-select-link trace-select-link-selected');
        })

    updateTraceChart(traceId)
}

const updateErrorChart = (traceId) => {
    d3.select('#error-chart').html("");
    d3.select('#error-span-durations').html("");
    embed(
        '#error-chart',
        `error_chart/${traceId}`
    ).catch(console.error);
    embed(
        '#error-span-durations',
        `error_span_durations/${traceId}`,
        {width: 875}
    ).catch(console.error);
    d3.json(`error_span_durations_summary/${traceId}`).then(data => {
        d3.select('#error-span-durations-summary')
          .selectAll('h6')
          .data(data)
          .join('h6')
          .text(d => d);
    });
}

const errorExplorer = (traceName, traces) => {
    const charts = newUi(`${traceName} Error Explorer`);
    const traceIds = traces.map(t => trace.getRoot(t).id);

    const crow = charts
        .append('div')
        .attr('class', 'row');

    const vizCol = crow
        .append('div')
        .attr('class', 'col');
    
    vizCol.append('div')
        .attr('class', 'row')
        .append('div')
        .attr('class', 'col')
        .attr('id', 'error-chart');
    
    vizCol.append('div')
        .attr('class', 'row')
        .append('div')
        .attr('class', 'col')
        .attr('id', 'error-span-durations-summary');
    
    vizCol.append('div')
        .attr('class', 'row')
        .append('div')
        .attr('class', 'col')
        .attr('id', 'error-span-durations');

    const traceNavCol = crow
        .append('div')
        .attr('class', 'col col-sm')
        .attr('id', 'error-trace-list');

    traceNavCol.append('ul')
        .selectAll('li')
        .data(traceIds)
        .join('li')
        .append('a')
        .attr('class', 'trace-select-link')
        .text(d => d)
        .on('click', (e, i) => {
            updateErrorChart(i);
            // reset existing selected...
            d3.selectAll('.trace-select-link').attr('class', 'trace-select-link');
            d3.select(e.target).attr('class', 'trace-select-link trace-select-link-selected');
        })

    updateErrorChart(traceIds[0])
}

const traceDrillDown = (traceName, traces) => {
    // transition the UI
    const charts = newUi(traceName);

    // trace summary
    charts
        .append('div')
        .attr('class', 'row')
        .append('div')
        .attr('class', 'col')
        .append('h4')
        .text('Minute-by-Minute Average Latencies per Span');

    const summary = charts
        .append('div')
        .attr('class', 'row')
        .append('div')
        .attr('class', 'col');
    const times = d3.extent(d3.merge(traces).map(t => t.timestamp));
    summary.text(`Start: ${dateFromTimestamp(times[0])}, Stop: ${dateFromTimestamp(times[1])}`);

    // heatmap
    const heatRow = charts
        .append('div')
        .attr('class', 'row');

    const heatmap = heatRow.append('div')
        .attr('class', 'col')
        .append('svg')
        .attr('viewBox', `0, 0, 800, 300`);

    const histo = heatRow.append('div')
        .attr('class', 'col');
        
    th.traceHeatmap(heatmap, histo, traces);
}

const dashboard = (traces) => {
    const charts = newUi("Dashboard");

    let traceRoots = d3.group(traces, t => trace.getSpanName(trace.getRoot(t)));
    let rootCounts = Array.from(traceRoots.entries(), x => ({
        name: x[0], 
        count: x[1].length, 
        traces: x[1], 
        errorTraces: trace.errorTraces(x[1])
    }));

    const traceRows = charts.selectAll('div')
                            .data(pairUp(rootCounts))
                            .join('div')
                            .attr('class', 'row');
    
    const cols = 2;
    const traceCol = (row, i, el) => { 
        const r = d3.select(el[i]);
        for (let x = 0; x < cols; x++) {
            const col = r.append('div').attr('class', 'col');
            if (row[x]) {
                col.attr('class', 'col trace_summary');
                col.append('h3').text(d => row[x].name);
                col.on('click', () => traceDrillDown(row[x].name, row[x].traces));

                const counts = col.append('h5').text(d => `${row[x].count} traces.`);
                if (row[x].errorTraces.length > 0) {
                    counts.append('span')
                          .attr('class', 'error_count')
                          .text(` ${row[x].errorTraces.length} with errors.`)
                          .on('click', (e) => {
                              e.stopPropagation();
                              errorExplorer(row[x].name, row[x].errorTraces);
                          });
                }

                const stDiv = col.append('div').attr('class', 'structure_tree');
                const countForest = trace.getFQNCounts(row[x].traces);
                const traceStructure = trace.countStratify(trace.fqnCountsToParentChild(countForest));
                st.structureTree(traceStructure, stDiv, {boxHeight: 250, width: 600});
            }
        }
    }

    traceRows.each(traceCol);
}

d3.json("./trace-files.json").then((traceList) => {
    const promises = traceList.slice(0, MAX_TRACES_TO_LOAD)
                              .map(f => d3.json(`data/synthetic/20210302-hipster-shop/${f}`)
                              .catch(function(error){
                                  // some traces didn't fully load from zipkin API
                                  console.log(`Error loading trace file: ${error}`);
                                  return [];
                              }));


    const traces = Promise.all(promises).then(traces => {
        // some of the traces in the collection are bogus
        let goodTraces = traces.filter(x => x.length > 0);
        goodTraces.forEach(t => trace.setSpanMetadata(t));

        const traceIds = goodTraces.map(t => trace.getRoot(t).id);
        const traceSearch = d3.select('#trace-search');
        traceSearch.on("keypress", (e, i) => {
            if(e.keyCode === 32 || e.keyCode === 13){
                traceExplorer(traceSearch, traceIds);
            }});

        d3.select('a.navbar-brand').on('click', () => dashboard(goodTraces));
        dashboard(goodTraces);
    });

});