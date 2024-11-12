local python = require("shihao.python")

local function check_global_key(iter)
    local status, res = pcall(function()
        for _, v in ipairs(iter) do
            if _G[v] then
                error("KeyError: " .. tostring(v))
            end
        end
        return 1, 2, 3
    end)
    if not status then
        error(res, 2)
    end

end

function str_fmt(formatstring, ...)
    return string.format(formatstring, python.map(tostring, ...))
end

check_global_key({ "str_fmt" })
