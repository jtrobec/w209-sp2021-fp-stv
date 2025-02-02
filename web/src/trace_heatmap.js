import * as d3 from 'd3';
import * as scales from 'd3-scale-chromatic';
import * as lg from 'd3-svg-legend';
import * as trace from './trace.js';
import * as v from 'vega';
import * as vl from 'vega-lite';
import * as vla from 'vega-lite-api';
import * as vtt from 'vega-tooltip';

const defaults = ({
    width: 800,
    height: 300,
    margin: {top: 10, left: 10, bottom: 10, right: 10},
    yAxisWidth: 100,
    xAxisHeight: 50,
    granularity: 'm'
});

const getTimeCoefficient = (gran) => {
    if (gran === '5m') {
        return 1000 * 1000 * 60 * 5;
    } else {
        return 1000 * 1000 * 60;
    }
}

const getTimeBuckets = (timeRange, timeBucket, timeCoef) => {
    let timeBuckets = [];
    for (let cur = timeBucket(timeRange[0]); cur <= timeBucket(timeRange[1]); cur += timeCoef) {
        timeBuckets.push(cur);
    }
    return timeBuckets;
}

const vegaInit = () => {
    const options = {
        config: {
            // Vega-Lite default configuration
        },
        init: (view) => {
            // initialize tooltip handler
            view.tooltip(new vtt.Handler().call);
        },
        view: {
            // view constructor options
            renderer: "svg",
        },
    };

    // register vega and vega-lite with the API
    vla.register(v, vl, options);
}

vegaInit();

const drawDurationHistogram = (spans, histo, durationRange) => {
    histo.html('');
    const dat = binDurations(50, durationRange, spans);

    // render a histogram of timings
    vla.markBar()
        .title('Histogram of Durations')
        .width(1000)
        .data(dat)
        .encode(
            vla.x().fieldQ("start").title('Duration (micros)'),
            vla.x2().fieldQ("end"),
            vla.y().fieldQ("count").scale({domain: [0, 350]}).title('Count of Spans')
        )
        .render()
        .then(viewElement => {
            // render returns a promise to a DOM element containing the chart
            // viewElement.value contains the Vega View object instance
            histo.node().appendChild(viewElement);
        });
};

const clearDurationHistogram = (histo) => {
    histo.html('');
    histo.append('div')
        .attr('class', 'row')
        .append('div')
        .attr('class', 'col')
        .style('text-align', 'center')
        .append('h5')
        .text('Mouse over a square in the heatmap to see a histogram of the span durations for that minute...');
};

const binDurations = (chunks, durationRange, spans) => {
    const bucketWidth = durationRange[1]/chunks;
    const thresholds = d3.range(0, durationRange[1], bucketWidth) 
    const binner = d3.bin().thresholds(thresholds);
    let buckets = binner(spans.map(s => s.duration));
    for (; buckets.length < thresholds.length; buckets.push([])) { }
    return d3.zip(thresholds, buckets).map(([t, b]) => ({start: t, end: t + bucketWidth - 1, count: b.length}));
}

export const traceHeatmap = (svg, heatleg, histo, traces, config=defaults) => {
    const conf = {...defaults, ...config};
    const timeRange = d3.extent(d3.merge(traces).map(t => t.timestamp));
    const durationRange = d3.extent(d3.merge(traces).map(t => t.duration));
    const heatmapWidth = conf.width - conf.margin.left - conf.margin.right - conf.yAxisWidth;
    const heatmapHeight = conf.height - conf.margin.top - conf.margin.bottom - conf.xAxisHeight;

    clearDurationHistogram(histo);

    const timeCoef = getTimeCoefficient(conf.granularity);
    const timeBucket = (time) => Math.floor(time / timeCoef) * timeCoef;
    const timeBuckets = getTimeBuckets(timeRange, timeBucket, timeCoef);

    // preliminary tree agg
    const fqnGrouped = d3.group(d3.merge(traces), t => t.fullyQualifiedName);
    const fqnRollup = Array.from(fqnGrouped).map(([k, v]) => ({
        fqn: k,
        count: v.length,
        averageDuration: d3.mean(v, s => s.duration),
        tbAvgDurs: Array.from(d3.group(v, s => timeBucket(s.timestamp))).map(([t, sps]) => ({timeBucket: t, avgDur: d3.mean(sps, sp => sp.duration), spans: sps}))
    }));
    const fqnFlattened = fqnRollup.flatMap(f => f.tbAvgDurs.map(ad => ({fqn: f.fqn, timeBucket: ad.timeBucket, avgDur: ad.avgDur, spans: ad.spans})));

    const countForest = trace.getFQNCounts(traces);
    const traceStructure = trace.countStratify(trace.fqnCountsToParentChild(countForest));
    let fqnsInDfsOrder = [];
    let depths = new Set();
    traceStructure.eachBefore(n => {
        fqnsInDfsOrder.push(n.data.fullyQualifiedName);
        depths.add(n.depth);
    });
    depths = Array.from(depths).sort();

    // create scales
    const heatmapXScale = d3.scaleBand().domain(timeBuckets).range([0, heatmapWidth]).paddingInner(0.02);
    const heatmapYScale = d3.scaleBand().domain(fqnsInDfsOrder).range([0, heatmapHeight]).paddingInner(0.02);
    const heatmapColorScale = d3.scaleSequentialLog(scales.interpolateViridis).domain([1, durationRange[1]]);
    // const heatmapColorScale = d3.scaleSequential(scales.interpolateViridis).domain([1, durationRange[1]]);

    const yAxisXScale = d3.scaleBand().domain(depths).range([0, 20]);

    // draw heatmap
    const heatmap = svg.append('g')
        .attr('transform', `translate(${conf.margin.left + conf.yAxisWidth}, ${conf.margin.top})`);
    heatmap.selectAll('rect')
        .data(fqnFlattened)
        .join('rect')
        .attr('x', d => heatmapXScale(d.timeBucket))
        .attr('width', heatmapXScale.bandwidth())
        .attr('y', d => heatmapYScale(d.fqn))
        .attr('height', heatmapYScale.bandwidth())
        .attr('fill', d => heatmapColorScale(d.avgDur))
        .on('mouseover', (e, d) => {
            d3.select(e.target).attr('stroke', 'cornflowerblue');
            drawDurationHistogram(d.spans, histo, durationRange);
        })
        .on('mouseleave', (e, d) => {
            d3.select(e.target).attr('stroke', null);
        });
    heatmap.on('mouseleave', (e, d) => clearDurationHistogram(histo));

    // x-axis
    svg.append('g')
       .attr('class', 'heatmap-x-axis')
       .attr('transform', `translate(${conf.margin.left + conf.yAxisWidth}, ${conf.margin.top + heatmapHeight})`)
       .call(d3.axisBottom(heatmapXScale).tickFormat(v => {
           let dt = new Date(v/1000.0);
           return d3.timeFormat('%M:%S')(dt);
       }));

    // y-axis
    const yAxis = svg.append('g')
       .attr('class', 'heatmap-y-axis')
       .attr('transform', `translate(${conf.margin.left}, ${conf.margin.top})`);

    const legend = heatleg.append("g")
       .attr("class", "legend")
       .attr("transform", `translate(${conf.margin.left},${conf.margin.top})`);

    const legendLinear = lg.legendColor()
                .title('Duration (micros)')
                .shapeWidth(30)
                .cells(10)
                .orient('vertical')
                .labelFormat('.2s')
                .scale(heatmapColorScale);

    legend.call(legendLinear);

    const yAxisPillHeight = 25;

    const yAxisEntry = (entryG) => {
        entryG.append('rect')
            .attr('width', d => conf.yAxisWidth - yAxisXScale.bandwidth() - yAxisXScale(d.depth))
            .attr('height', yAxisPillHeight)
            .attr('transform', `translate(0, ${(heatmapYScale.bandwidth() / 2.0) - (yAxisPillHeight / 2.0)})`)
            .attr('rx', 5)
            .attr('ry', 5)
            .attr('fill', '#ccc');
        const lab = entryG.append('text')
            .attr('transform', `translate(5, ${heatmapYScale.bandwidth() / 2.0})`);
        lab.append('tspan')
            .attr('x', '0.05em')
            .text(d => d.data.shortName.split('/')[0].toUpperCase());
        lab.append('tspan')
            .attr('x', '0.05em')
            .attr('dy', '1em')
            .text(d => d.data.shortName.split('/')[1]);
    };
    yAxis.selectAll('g')
       .data(traceStructure)
       .join('g')
       .attr('transform', d => `translate(${yAxisXScale(d.depth)}, ${heatmapYScale(d.data.fullyQualifiedName)})`)
       .call(yAxisEntry);
    yAxis.append("g")
        .attr('transform', `translate(0, ${(heatmapYScale.bandwidth() / 2.0)})`)
        .attr("fill", "none")
        .attr("stroke", "#ccc")
        .attr("stroke-opacity", 1)
        .attr("stroke-width", 1.5)
        .style("pointer-events", "none")
        .selectAll('path')
        .data(traceStructure.links())
        .join('path')
        .style("pointer-events", "none")
        .attr("d", ({source, target}) => {
                const startX = yAxisXScale(source.depth), startY = heatmapYScale(source.data.fullyQualifiedName);
                const xMove = yAxisXScale(target.depth), yMove = heatmapYScale(target.data.fullyQualifiedName);
                return `M${startX} ${startY} V ${yMove} H ${xMove}`;
        });
}