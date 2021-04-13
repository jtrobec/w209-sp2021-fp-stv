import 'bootstrap';
import 'bootstrap/dist/css/bootstrap.min.css';
import 'bootstrap-icons/font/bootstrap-icons.css';
import './custom.css'

import * as d3 from 'd3';
import embed from 'vega-embed';
import * as st from './structure_tree.js';
import * as th from './trace_heatmap.js'
import * as trace from './trace.js';
import { schemeDark2 } from 'd3';

const MAX_TRACES_TO_LOAD = 5000;

/**
 * Given an array, group the elements into pairs.
 *
 * @param {array} arr
 * @returns an array of arrays of 2 elements, last entry may have only 1
 */
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

/**
 * Convert a unix, microsecond timestamp into a Date object.
 * @param {long} timestamp
 * @returns the timestamp as a Date.
 */
const dateFromTimestamp = (timestamp) => new Date(timestamp / 1000);

const newUi = (title) => {
    d3.select('#current-view').text(title);
    d3.select(".struct-tip").style("opacity", 0);
    const charts = d3.select('.charts');
    charts.html("");
    const info = d3.select('#info');
    info.html("");

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

const updateAggChart = (traceType) => {
    d3.select('#current-view').text(`${traceType} Trace Explorer`);
    embed(
        '#trace-tree-chart',
        `trace_tree_chart_agg/${traceType}`,
        {width: 875}
    ).catch(console.error);
}

const traceExplorer = (traceId, traceIds) => {
    history.pushState({last: "trace-explorer"}, "Trace Visualization - Trace Explorer", "?te");
    const charts = newUi(`${traceId} Trace Explorer`);
    const crow = charts
        .append('div')
        .attr('class', 'row');
    crow.append('h5')
        .text('Single Trace Explorer');
    crow.append('p')
        .html('Two different views of the same trace. The waterfall view shows the duration of each span, if it errored, and the order of completion for this specific trace. '
        + "Meanwhile, the tree view shows the trace's heirarchy. "
        + 'Both plots feature a tooltip that can be toggled by hovering your cursor over on a bar in the plot. '
        + "Compare similar traces by clicking on the trace ID's below.");

    const crow1 = crow
        .append('div')
        .attr('class', 'row');

    const vizCol = crow1
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
        {width: 680}
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
    history.pushState({last: "error-explore"}, "Trace Visualization - Error Explorer", "?ee");
    const charts = newUi(`${traceName} Error Explorer`);
    const traceIds = traces.map(t => trace.getRoot(t).id);

    const crow = charts
        .append('div')
        .attr('class', 'row');
    crow.append('h5')
        .text('Traces with Errors');
    crow.append('p')
        .html('<p>The list of <em>trace IDs</em> shows you all traces that hit at least one error. Select a <em>trace ID</em> to view all spans within the trace and explore the spans that hit an error in the <em>waterfall chart</em>. Scroll over the bars to get more information in the tooltip.</p>'
        + '<p>In the <em>span duration histograms</em>, visualize the erroneous spans from the selected trace within the context of all other spans for the same service to understand the distribution of durations for the given span.</p>'
        + '<b>Interactions: </b>Scroll over the bars to get more information in the tooltip. Zoom into the charts by pinching your trackpad or using your mouse scroller. Pan by clicking and dragging inside the charts.');


    const vizCol = crow
        .append('div')
        .attr('class', 'col')


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

    traceNavCol.append('h6')
        .text('List of Traces with Errors');

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
    history.pushState({last: "trace-drill"}, "Trace Visualization - Trace Drill Down", "?tdd");
    // transition the UI
    const charts = newUi(traceName);
    const times = d3.extent(d3.merge(traces).map(t => t.timestamp));

    const info = d3.select('#info');
    info.append('h5')
        .text('Aggregate Trace Views.');
    info.append('p')
        .html('Drill into minute-by-minute timings of trace latencies using the trace heatmap, or look at an aggregated view of the trace tree.');

    const accordion = charts
        .append('div')
        .attr('class', 'row')
        .append('div')
        .attr('class', 'col')
        .append('div')
        .attr('class', 'accordion')
        .attr('id', 'explore-accordion');

    const addAccordionItem = (name, header, expanded) => {
        const item = accordion
            .append('div')
            .attr('class', 'card');
        item.append('div')
            .attr('class', 'card-header')
            .attr('id', `acc-${name}-header`)
            .append('h2')
            .attr('class', 'mb-0')
            .append('button')
            .attr('class', `btn btn-link ${expanded ? '' : 'collapsed'}`)
            .attr('type', 'button')
            .attr('data-toggle', "collapse")
            .attr('data-target', `#acc-${name}-div`)
            .text(header);
        return item.append('div')
            .attr('id', `acc-${name}-div`)
            .attr('class', `collapse ${expanded ? 'show' : ''}`)
            .attr('aria-labelledby', `acc-${name}-header`)
            .attr('data-parent', "#explore-accordion")
            .append('div')
            .attr('class', "card-body");
    };
    const heatAcc = addAccordionItem('heatmap', 'Trace Durations Heatmap', true);

    // heatmap
    const desc = heatAcc
        .append('div')
        .attr('class', 'row')
        .append('div')
        .attr('class', 'col');
    desc.append('h4')
        .text('Minute-by-Minute Average Latencies per Span');
    desc.append('p')
        .html('The heatmap below shows the average duration of spans starting in a given minute. Mouse over the '
        + 'minute/span to see a histogram of durations for spans starting in that minute. The y-axis shows the structure '
        + 'of the trace tree.')

    const summary = heatAcc
        .append('div')
        .attr('class', 'row')
        .append('div')
        .attr('class', 'col');
    summary.html(`<em>Start:</em> ${dateFromTimestamp(times[0])}, <em>Stop:</em> ${dateFromTimestamp(times[1])}`);

    const heatRow = heatAcc
        .append('div')
        .attr('class', 'row');

    const heatmap = heatRow.append('div')
        .attr('class', 'col')
        .append('svg')
        .attr('viewBox', `0, 0, 800, 300`);

    const heatleg = heatRow.append('div')
        .attr('class', 'col-sm-3')
        .style('word-wrap', 'normal')
        .append('svg')
        .attr('viewBox', `0, 0, 400, 400`)

    const histo = heatAcc.append('div')
        .attr('class', 'row')
        .append('div')
        .attr('class', 'col');

    th.traceHeatmap(heatmap, heatleg, histo, traces);

    const treeAcc = addAccordionItem('tree', 'Aggregate Trace Tree', false);

    treeAcc.append('div')
            .attr('class', 'row')
            .append('div')
            .attr('class', 'col')
            .append('h4').text('Aggregate Trace Tree View');
    treeAcc.append('p')
            .html("The plot below shows how long each span's duration on average as well as the most common tree fanout for this "
            + 'trace. Using your mouse you can hover over each bar in the plot to pull up a tooltip with more specific infromation relating to the span. '
            + 'The bars are shaded to represent the error rate for the specific span.')
            .append('div')
           .attr('id', 'trace-tree-chart');
    updateAggChart(traceName);
}

const dashboard = (traces) => {
    history.pushState({last: "dash"}, "Trace Visualization - Dashboard", "?dash");
    const charts = newUi("Dashboard");

    const info = d3.select('#info');
    info.append('h5')
        .text('Below are the traces in the current dataset.');
    info.append('p')
        .html('Click on a <em>trace card</em> to explore span durations over time, click on an <em>error count</em> '
        + 'to get information about traces with errors, or, enter a <em>trace ID</em> into the search bar above '
        + 'to explore an individual trace.');

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
                col.on('click', () => {
                    traceDrillDown(row[x].name, row[x].traces);
                });

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

d3.json("data/synthetic/20210409-hipster-shop-sl.json").then((allSpans) => {
    const traces = Array.from(d3.group(allSpans, x => x.traceId)).map(([k, v]) => v);
    traces.forEach(t => trace.setSpanMetadata(t));

    const traceIds = traces.map(t => trace.getRoot(t).id);
    const traceSearch = d3.select('#trace-search');
    traceSearch.on("keypress", (e, i) => {
        if(e.keyCode === 32 || e.keyCode === 13){
            traceExplorer(traceSearch.node().value, traceIds);
        }});
    d3.select('#load-trace-button').on("click", (e, i) => {
        traceExplorer(traceSearch.node().value, traceIds);
    })

    d3.select('a.navbar-brand').on('click', () => dashboard(traces));

    window.onpopstate = (e) => {
        if (e.state.last === "dash") {
            dashboard(traces);
        }
    };
    dashboard(traces);
});
