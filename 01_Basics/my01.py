import unreal
import os    # 操作系统工具箱：拼文件路径、查文件时间要用它（练习3会用）
import time  # 时间工具箱：把时间戳变成 "2026-09-13 20:30:00" 这种看得懂的样子

unreal.log('-' * 50)

# print("=" * 50)
# print("Hello, Unreal Engine!")
# print("=" * 50)

# print(unreal.Paths.project_content_dir())

# all_classes = [name for name in dir(unreal) if not name.startswith('_')]
# unreal.log(f"unreal 模块包含 {len(all_classes)} 个类/函数")

# ─────────────────────────────────────────────────────────
# 🎯 练习题
# ─────────────────────────────────────────────────────────
# 1. 修改代码，只列出 /Game/Characters 路径下的资产
# 2. 统计项目中每种类型的资产各有多少个
# 3. 找到项目中最近创建的5个资产（提示：查看 find_asset_data 的返回值）
#
# 提示：可以用 unreal.log 输出到 UE 的输出日志窗口查看结果

# ─────────────────────────────────────────────────────────
# ✅ 练习1：只列出 /Game/Characters 路径下的资产
#    这题你做对了！把 list_assets 的参数从 "/Game" 换成 "/Game/Characters" 就是正确答案。
# ─────────────────────────────────────────────────────────
all_assets = unreal.EditorAssetLibrary.list_assets("/Game/Characters", recursive = False)
for asset_path in all_assets:
    asset_data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
    unreal.log(f"资产：{asset_data.asset_class_path.asset_name}")

cnt = dict()
all_assets = unreal.EditorAssetLibrary.list_assets("/Game")

# ─────────────────────────────────────────────────────────
# 🔧 练习2：统计每种资产类型各有多少个
#    你原来的代码里有 4 个错误，下面在出错的位置逐个讲解。
# ─────────────────────────────────────────────────────────
for asset_path in all_assets:  # 小建议：循环变量叫 asset_path 比叫 i 更清楚，
                               # 一眼就知道"手里拿的这是一条资产路径"

    # ❌ 你原来的写法：type_name = type(all_assets.get_name()).__name__
    #    这一行里藏着 3 个错误：
    #
    #    错误① all_assets 是一个【列表】（一篮子路径字符串）。
    #          列表这个"容器"本身没有 .get_name() 方法，运行到这里会直接报错：
    #          AttributeError: 'list' object has no attribute 'get_name'
    #          要打交道的应该是【循环变量】（篮子里的每一个），而不是整个篮子。
    #
    #    错误② 那改成 asset_path.get_name() 行不行？还是不行！
    #          因为 list_assets 给我们的循环变量是【字符串】（路径文本），
    #          字符串同样没有 .get_name()。字符串只是"地址"，
    #          拿着地址是问不出"这个资产是什么类型"的。
    #
    #    错误③ type(x).__name__ 告诉你的是"x 在 Python 里是什么类型"
    #          （比如 str、list），而不是"资产在引擎里是什么类别"。
    #          一个是 Python 世界的概念，一个是引擎世界的概念，搞混了。
    #
    # ✅ 正确答案：先用 find_asset_data(路径) 按"地址"把资产的档案调出来，
    #    档案里的 asset_class_path.asset_name 才是资产真正的类别名。
    asset_data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
    type_name = str(asset_data.asset_class_path.asset_name)

    """
    （小字备注：UE4 里写作 str(asset_data.asset_class)，UE5 起改成了上面这种）
    思考题：先 load_asset 再 type(x).__name__ 行不行？
    obj = unreal.EditorAssetLibrary.load_asset(asset_path)
    type_name = type(obj).__name__        # ← 这样确实能拿到引擎类型名！
    因为 UE 的 Python 插件给每个引擎类都生成了同名的 Python 类，
    load 一个 Texture2D 得到的对象，type() 出来就叫 "Texture2D"。
    但【统计】时仍推荐 find_asset_data，原因见下方"思考题解答"区块。
    """
    
    # ❌ 你原来的写法：
    #        key = cnt.keys()
    #        if type_name in key:
    #            cnt[type_name] += 1
    #
    #    错误④：少了 else！仔细推演一下：某种类别【第一次】出现时，
    #    它还不在这个空字典里 → if 条件不成立 → 什么都不做，直接跳过。
    #    也就是说，任何类别都永远等不到"被 +1"的那一天，
    #    循环跑完后 cnt 还是个空字典，最后一行什么都打印不出来。
    #    （另外 key = cnt.keys() 这行是多余的，`in cnt` 直接就能查字典。）
    #
    # ✅ 正确答案：第一次见到就登记为 1，之后再见到才 +1：
    if type_name in cnt:
        cnt[type_name] += 1
    else:
        cnt[type_name] = 1
    # （进阶一行流，与上面四句完全等价：
    #     cnt[type_name] = cnt.get(type_name, 0) + 1
    #   dict.get(键, 默认值) 的意思是"有这个键就取它的值，没有就给我默认值"）

for u, v in cnt.items():  # ✅ 这段你写对了：items() 把字典拆成一对对(键, 值)来遍历
    unreal.log(f"{u}: {v} 个")

# 备注：练习2题目原文说的是"项目中"每种类型各多少。上面顺着练习1
# 统计的是 /Game/Characters 里的；想统计整个项目，把 list_assets
# 的参数改回 "/Game" 即可，其余代码一个字都不用动。

# ─────────────────────────────────────────────────────────
# ✅ 练习3：找到项目中最近创建的5个资产（补完）
#
# 深入浅出讲思路：
#   提示让我们去看 find_asset_data 的返回值（AssetData 资产档案）。
#   翻一翻这份档案会发现：里面其实【没有】直接存"创建时间"！
#   那怎么办？换个角度——每个资产在硬盘上都是一个真实的 .uasset 文件，
#   文件的修改时间 ≈ 它最近一次创建/保存的时间。
#   所以路线是：
#     资产路径 → find_asset_data 拿档案 → 读档案里的 package_name（包名）
#     → 拼出磁盘上的 .uasset 文件 → 查文件时间 → 按时间排序 → 取前5名
# ─────────────────────────────────────────────────────────

project_assets = unreal.EditorAssetLibrary.list_assets("/Game")  # 题目说"项目中"，根目录用 /Game
content_dir = unreal.Paths.project_content_dir()  # Content 文件夹在磁盘上的真实位置

def get_asset_file_time(asset_path):
    """传入一条资产路径，返回它对应 .uasset 文件的修改时间（时间戳，数字越大越新）"""
    asset_data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
    package_name = str(asset_data.package_name)  # 例如 "/Game/Characters/BP_Hero"

    # 引擎里的 "/Game/xxx" 对应磁盘上的 "<Content目录>/xxx.uasset"，
    # 所以把开头的 "/Game/" 去掉，再接到 content_dir 后面：
    rel_path = package_name.replace("/Game/", "", 1)
    file_path = os.path.join(content_dir, rel_path + ".uasset")

    if os.path.exists(file_path):
        return os.path.getmtime(file_path)  # mtime = modification time，文件最后修改时间
        # （小知识：Windows 上还有个 os.path.getctime()，那才是严格意义的"创建时间"，
        #   想学得更深可以换成它对比看看。）
    return 0  # 文件不存在（极少数情况，比如引擎内置资产）就把它当作最老的

# sorted(列表, key=规则, reverse=True)：
#   key= 告诉 sorted "按什么标准比大小"——这里按每个资产的文件时间；
#   reverse=True 表示从大到小排，让"最新"的排在最前面（默认是从小到大）。
sorted_by_time = sorted(project_assets, key=get_asset_file_time, reverse=True)

unreal.log("──── 最近创建的5个资产 ────")
for asset_path in sorted_by_time[:5]:  # 列表切片 [:5] ＝ 只取前 5 个
    time_str = time.strftime("%Y-%m-%d %H:%M:%S",
                             time.localtime(get_asset_file_time(asset_path)))
    unreal.log(f"{time_str}  {asset_path}")

# ═════════════════════════════════════════════════════════
# 💡 思考题解答：load_asset + type(x).__name__ 也能拿到引擎类型，
#    为什么统计时还是推荐 find_asset_data？
#
#    打个比方：想知道图书馆里每种书各有多少本——
#      find_asset_data = 翻【目录卡片】：书名、分类都在卡片上，
#                        书还安安静静躺在书架上。查一万本也很快。
#      load_asset      = 把每本书【从书架上搬下来】翻开看封面：
#                        资产会被真正加载进内存（贴图解压、网格读入……），
#                        几百上千个资产跑一遍，又慢又可能把内存吃爆。
#
#    还有两个实战小坑：
#      ① load_asset 遇到损坏/引用丢失的资产会返回 None，
#         type(None).__name__ 是 "NoneType"，会悄悄污染你的统计，
#         得额外写 if obj is not None 来过滤。
#      ② 对蓝图资产，load 出来的对象类型是 "Blueprint"（资产本身），
#         不是"这个蓝图生成的那种东西"；想要生成的类要用
#         obj.generated_class()。find_asset_data 给的也是资产本身的
#         类别，所以做"资产类型统计"时两者结果一致。
#
#    一句话总结：【只想要信息】就查档案（find_asset_data），
#               【要真正使用资产】才去加载它（load_asset）。
# ═════════════════════════════════════════════════════════

unreal.log('-' * 50)