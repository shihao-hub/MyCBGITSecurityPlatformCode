local python = {}

function python.map(fn, ...)
    local args = { ... }
    args.n = select("#", ...)
    for i = 1, args.n do
        args[i] = fn(args[i])
    end
    return unpack(args, 1, args.n)
end

return python
