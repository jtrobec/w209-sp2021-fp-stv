import * as d3 from 'd3';

/**
 * Given a trace as an array of spans, returns the span that is the root of the
 * trace.
 * 
 * @param {*} spans     An array of span objects.
 */
export const getRoot = (spans) => {return spans.find(s => !(s.parentId));};

/**
 * Gets the name of a span.
 * 
 * @param {*} span      The span. 
 * @returns The span's name.
 */
export const getSpanName = (span) => {return span.localEndpoint.serviceName + span.name;};

export const errorTraceCount = (traces) => { return traces.map(hasError).reduce((acc, cur) => cur ? acc + 1 : acc, 0) }

export const hasError = (spans) => {return (spans.find(s => s.tags?.error === 'true') != undefined)}

/**
 * Given a specific span in a trace (collection of spans), returns the fully
 * qualified name of the span. This includes the names of all parent spans,
 * ending with the name of the current span.
 * 
 * @param {*} span      The span for which we want the FQN.
 * @param {*} spans     The collection of spans in the trace.
 * @returns The span's fully qualified name.
 */
export const getFullyQualifiedSpanName = (span, spans) => {
    const spanShortName = getSpanName(span);
    if (span.parentId) {
        return `${getFullyQualifiedSpanName(parentSpan, spans)}->${spanShortName}`;
    } else {
        return spanShortName;
    }
};

/**
 * Given an array of spans representing a trace, sets additional metadata on
 * each span that relates to the overall trace structure. For example, we set
 * depth and qualified names for each span.
 * 
 * @param {Array} spans 
 */
export const setSpanMetadata = (spans) => {
    let root = getRoot(spans);
    let state = {
        spans,
        depth: 0,
        currentQualifiedName: ''
    };
    setSpanProps(state, root);
};

/**
 * A helper function for setSpanMetadata that recurses through the tree of a
 * trace, setting various properties like FQN and depth.
 * @param {Object} state 
 * @param {*} span 
 */
const setSpanProps = (state, span) => {
    span.depth = state.depth;
    span.shortName = getSpanName(span);
    span.fullyQualifiedName = `${state.currentQualifiedName}${span.shortName}`;

    let children = state.spans.filter(s => s.parentId == span.id);
    children.forEach(child => {
        let newState = {
            ...state,
            depth: state.depth + 1,
            currentQualifiedName: `${span.fullyQualifiedName}->`
        };
        setSpanProps(newState, child);
    });
};

/**
 * Given a set of traces that have been decorated with FQN via setSpanMetadata,
 * this function builds counts of each FQN for all the traces. This is a way of
 * counting all the straight paths taken through trace trees.
 * 
 * @param {Array} traces 
 * @returns 
 */
export const getFQNCounts = (traces) => {
    let counts = {}
    traces.forEach(trace => trace.forEach(s => {
        counts[s.fullyQualifiedName] = (counts[s.fullyQualifiedName] ?? 0) + 1; 
    }))
    return counts;
}

/**
 * Convert a dictionary of FQN counts into a table of parent-child
 * relationships. This is a way to recover trace structure after flattening
 * when counting up node visits over a set of traces.
 * 
 * @param {*} countForest 
 * @returns 
 */
export const fqnCountsToParentChild = (countForest) => Object.entries(countForest).map(([k, v]) => {
    const lastArrow = k.lastIndexOf('->');
    if (lastArrow >= 0) {
        return {
            fullyQualifiedName: k,
            shortName: k.slice(lastArrow + 2),
            parentFullyQualifiedName: k.slice(0, lastArrow),
            count: v
        }
    } else {
        return {
            fullyQualifiedName: k,
            shortName: k,
            count: v
        };
    }
});

export const countStratify = d3.stratify()
                               .id(d => d.fullyQualifiedName)
                               .parentId(d => d.parentFullyQualifiedName);
