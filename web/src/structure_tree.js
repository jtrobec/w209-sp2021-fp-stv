import * as d3 from 'd3';
import * as lg from 'd3-svg-legend';
import * as trace from './trace.js'

const defaults = ({
    boxHeight: 200,
    margin: {top: 10, left: 10, bottom: 60, right: 10}
});

// Define the div for the tooltip
const tip = d3.select("body").append("div")	
                .attr("class", "struct-tip")				
                .style("opacity", 0);

export const structureTree = (traceHierarchy, treeDiv, config = defaults) => {
    const conf = {...defaults, ...config};
    const width = conf.width ?? treeDiv.node().getBoundingClientRect().width;
    const height = conf.boxHeight ?? (width * 0.33);
    const margin = conf.margin;
    const inner = {width: width - margin.left - margin.right, height: height - margin.top - margin.bottom}
    const svg = treeDiv.append("svg").attr('viewBox', [0, 0, width, height]);
    
    // count the number of nodes we have on each level
    let maxDepth = 0;
    let levelIndex = 0;
    let lastDepth = 0;
    let maxLevelIndex = 0;
    traceHierarchy.each((node) => {
        // d3-hierarchy node.each goes in depth first order, so this gives us an index
        // for the node's global position in the level
        if (node.depth != lastDepth) {
            levelIndex = 0;
            lastDepth = node.depth;
        }
        maxDepth = d3.max([maxDepth, node.depth]);
        if (node.parent) {
            levelIndex = d3.max([levelIndex, node.parent.levelIndex]);
        }
        node.levelIndex = levelIndex;
        maxLevelIndex = d3.max([maxLevelIndex, levelIndex]);
        levelIndex += 1;
    });

    const range = (start, end) => Array.from({length: (end - start)}, (v, k) => k + start);

    const scaleX = d3.scaleBand()
                     .domain(range(0, 1+maxDepth))
                     .range([margin.left, width-margin.right])
                     .paddingInner(0.05);
    const scaleY = d3.scaleBand()
                     .domain(range(0, 1+maxLevelIndex))
                     .range([margin.top, height - margin.bottom])
                     .paddingInner(0.05);
    const scaleColor = d3.scaleSequential(d3.interpolateCividis)
                         .domain([0, traceHierarchy.data.count]);

    const legend = svg.append("g")
                      .attr("class", "legend")
                      .attr("transform", `translate(${margin.left},${height - margin.bottom})`);
   
    const legendLinear = lg.legendColor()
                            .title('Node Counts')
                            .shapeWidth(30)
                            .cells(5)
                            .orient('horizontal')
                            .labelFormat('d')
                            .scale(scaleColor);
    
    legend.call(legendLinear);

    const boxSize = d3.min([30, scaleX.bandwidth(), scaleY.bandwidth()]);
    const target = svg.append('g')
                      .attr('transform', `translate(${margin.left}, ${margin.top})`);

    target.append("g")
        .attr("fill", "none")
        .attr("stroke", "#555")
        .attr("stroke-opacity", 0.4)
        .attr("stroke-width", 1.5)
        .style("pointer-events", "none")
        .selectAll('path')
        .data(traceHierarchy.links())
        .join('path')
        .style("pointer-events", "none")
        .attr("d", d3.linkHorizontal()
            .x(n => scaleX(n.depth) + boxSize/2)
            .y(n => scaleY(n.levelIndex) + boxSize/2));

    target.append('g')
        .selectAll('rect')
        .data(traceHierarchy)
        .join('rect')
        .attr('x', n => scaleX(n.depth))
        .attr('y', n => scaleY(n.levelIndex))
        .attr('width', boxSize)
        .attr('height', boxSize)
        .attr('rx', 5)
        .attr('ry', 5)
        .attr('fill', n => scaleColor(n.data.count))
        .on("mouseover", (e, n) => {		
            tip.transition()		
               .duration(200)		
               .style("opacity", .9);		
            tip.html(`<strong>${n.data.shortName}</strong><br/>Count: ${n.data.count}`)	
               .style("left", (e.pageX) + "px")		
               .style("top", (e.pageY - 28) + "px");	
            })					
        .on("mouseout", d => {		
            tip.transition()		
               .duration(500)		
               .style("opacity", 0);	
        });
}