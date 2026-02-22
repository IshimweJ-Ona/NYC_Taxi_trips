// Manual algorithms for frontend data processing no Array.sort usage.
(function attachManualAlgorithms(globalScope) {
    function compareValues(left, right, ascending) {
        if (ascending) {
            return left <= right;
        }
        return left >= right;
    }

    function normalizeValue(value) {
        if (value === null || value === undefined) {
            return '';
        }
        return String(value).toLowerCase();
    }

    function mergeSortObjectsByField(items, field, ascending = true) {
        const size = items.length;
        if (size <= 1) {
            return items.slice(0);
        }

        let source = items.slice(0);
        let target = new Array(size);
        let width = 1;

        while (width < size) {
            let left = 0;
            while (left < size) {
                let mid = left + width;
                let right = left + (width * 2);
                if (mid > size) {
                    mid = size;
                }
                if (right > size) {
                    right = size;
                }

                let i = left;
                let j = mid;
                let k = left;

                while (i < mid && j < right) {
                    const leftValue = normalizeValue(source[i][field]);
                    const rightValue = normalizeValue(source[j][field]);
                    if (compareValues(leftValue, rightValue, ascending)) {
                        target[k] = source[i];
                        i += 1;
                    } else {
                        target[k] = source[j];
                        j += 1;
                    }
                    k += 1;
                }

                while (i < mid) {
                    target[k] = source[i];
                    i += 1;
                    k += 1;
                }

                while (j < right) {
                    target[k] = source[j];
                    j += 1;
                    k += 1;
                }

                left += width * 2;
            }

            const swap = source;
            source = target;
            target = swap;
            width *= 2;
        }

        return source;
    }

    function uniqueFieldValues(items, field) {
        const unique = [];
        let i = 0;
        while (i < items.length) {
            const candidate = items[i][field];
            if (candidate !== null && candidate !== undefined && candidate !== '') {
                let found = false;
                let j = 0;
                while (j < unique.length) {
                    if (unique[j] === candidate) {
                        found = true;
                        break;
                    }
                    j += 1;
                }
                if (!found) {
                    unique.push(candidate);
                }
            }
            i += 1;
        }
        return unique;
    }

    globalScope.ManualAlgorithms = {
        mergeSortObjectsByField,
        uniqueFieldValues
    };
})(window);
