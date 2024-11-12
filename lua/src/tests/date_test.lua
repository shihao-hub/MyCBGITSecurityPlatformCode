print(os.time())

local today_timestamp = os.time({
    year = 2024, month = 11, day = 7,
})
print(today_timestamp)
print(os.date())
print(os.date("%Y-%m-%d %H:%M:%S", today_timestamp))
print(os.date("*t", today_timestamp))
print(1 - 3 / 8)

local function all(n, ...)
    local varargs = { ... }
    for i = 1, n do
        if not varargs[i] then
            return false
        end
    end
    return true
end

print(all(3, 1, nil, 3))
