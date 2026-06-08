import os
import zipfile
import tarfile

def unzip_all(folder, delete_after=True, max_rounds=5):
    """
    简单通用解压函数：解压目录下所有 .zip 和 .tar 类型文件
    支持 .zip, .tar, .tar.gz, .tgz 等
    :param folder: 要解压的文件夹路径
    :param delete_after: 是否解压后删除原压缩包
    :param max_rounds: 最多解压几轮（防止无限循环）
    """
    print(f"开始解压 {folder} 中的压缩文件...\n")

    for round_num in range(max_rounds):
        found = False  # 标记本轮是否有文件被解压

        # 遍历所有文件
        for root, _, files in os.walk(folder):
            for file in files:
                filepath = os.path.join(root, file)

                # 处理 .zip
                if file.lower().endswith('.zip'):
                    try:
                        with zipfile.ZipFile(filepath, 'r') as z:
                            z.extractall(root)
                        print(f"✅ 解压: {file}")
                        if delete_after:
                            os.remove(filepath)
                            print(f"🗑️ 删除: {file}")
                        found = True
                    except Exception as e:
                        print(f"❌ 失败: {file} - {e}")

                # 处理 .tar, .tar.gz, .tgz, .tar.bz2
                elif file.lower().endswith(('.tar', '.tar.gz', '.tgz', '.tar.bz2')):
                    try:
                        with tarfile.open(filepath, 'r:*') as t:
                            t.extractall(root)
                        print(f"✅ 解压: {file}")
                        if delete_after:
                            os.remove(filepath)
                            print(f"🗑️ 删除: {file}")
                        found = True
                    except Exception as e:
                        print(f"❌ 失败: {file} - {e}")

        # 如果本轮没有解压任何文件，退出
        if not found:
            print(f"第 {round_num + 1} 轮完成，没有新文件可解压。\n")
            break
        else:
            print(f"第 {round_num + 1} 轮完成，继续检查是否有新解压出的压缩包...\n")

    print("✅ 所有能解压的文件已完成处理！")