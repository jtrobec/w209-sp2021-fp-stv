import 'bootstrap';
import 'bootstrap/dist/css/bootstrap.min.css';
import * as d3 from 'd3';

const MAX_TRACES_TO_LOAD = 500;

const getRoot = (spans) => {return spans.find(s => !(s.parentId));};
const getSpanName = (span) => {return span.localEndpoint.serviceName + span.name;};
const getFullyQualifiedSpanName = (span, spans) => {
    const spanShortName = getSpanName(span);
    if (span.parentId) {
        return `${getFullyQualifiedSpanName(parentSpan, spans)}->${spanShortName}`;
    } else {
        return spanShortName;
    }
};

d3.json("./trace-files.json").then((traceList) => {
    const promises = traceList.slice(0, MAX_TRACES_TO_LOAD)
                              .map(f => d3.json(`data/synthetic/20210302-hipster-shop/${f}`)
                              .catch(function(error){
                                  // some traces didn't fully load from zipkin API
                                  console.log(`Error loading trace file: ${error}`);
                                  return [];
                              }));

    const charts = d3.select('.charts').text('charts found');
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

    const traces = Promise.all(promises).then(traces => {
        // some of the traces in the collection are bogus
        let goodTraces = traces.filter(x => x.length > 0);
        let traceRoots = d3.group(goodTraces.map(getRoot), getSpanName);
        let rootCounts = Array.from(traceRoots.entries(), x => ({name: x[0], count: x[1].length}));

        let traceRows = charts.selectAll('div')
                              .data(pairUp(rootCounts))
                              .join('div')
                              .attr('class', 'row');
        
        const traceCol = (row, idx) => { 
            const col = traceRows.append('div')
                                 .attr('class', 'col');
            col.append('h3')
               .text(d => d[idx].name);
            col.append('h5')
               .text(d => `${d[idx].count} traces.`)
        }

        traceRows.each((r, i) => traceCol(r, i % 2));
            
    });

});