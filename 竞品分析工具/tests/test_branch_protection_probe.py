# 分支保护验证探针：故意失败的测试，用于确认 pytest Required check 会机械阻断 PR 合并
# 本文件只存在于探针分支，验证完成后随分支一起删除，绝不合并进 main
def test_branch_protection_probe_intentional_failure():
    assert False, "intentional failure: branch protection validation probe"