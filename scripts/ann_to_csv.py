import csv
import sys


def convert_ann_to_csv(ann_file_path, csv_file_path, valid_types):
    # 创建类型统计字典
    type_counts = {t: 0 for t in valid_types}

    # 创建输出的CSV文件
    with open(csv_file_path, 'w', newline='', encoding='utf-8') as csv_file:
        # 定义CSV文件的表头
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(
            ['term_index', 'type', 'start_pos', 'end_pos', 'mention', 'agent_type'])

        # 读取ann文件
        with open(ann_file_path, 'r', encoding='utf-8') as ann_file:
            for line in ann_file:
                # 跳过空行
                if not line.strip():
                    continue

                # 分割每行内容
                parts = line.strip().split('\t')
                if len(parts) < 3:
                    continue

                # 处理第二部分（类型和位置信息）
                type_and_pos = parts[1].split()
                if len(type_and_pos) < 3:
                    continue

                term_type = type_and_pos[0]  # 获取term类型

                # 检查类型是否在valid_types中
                if term_type not in valid_types:
                    continue

                # 更新类型计数
                type_counts[term_type] += 1

                term_index = parts[0]  # 获取term序号
                start_pos = type_and_pos[1]  # 获取开始位置

                # 处理 end_pos 可能包含多个数字的情况
                end_pos = type_and_pos[2]    # 获取结束位置
                if ';' in end_pos:
                    # 如果包含多个位置，取最大值
                    end_positions = [int(pos) for pos in end_pos.split(';')]
                    end_pos = str(max(end_positions))

                mention = parts[2]  # 获取term原文

                # 写入CSV文件
                csv_writer.writerow(
                    [term_index, term_type, start_pos, end_pos, mention, 'annotation'])

    # 输出类型统计信息
    print("\n类型统计:")
    for type_name, count in type_counts.items():
        if count == 0:
            print(f"警告: 类型 '{type_name}' 在文件中未出现")
        else:
            pass  # print(f"类型 '{type_name}' 出现 {count} 次")


def main():
    ann_file_path = "/home/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/data/21.ann"
    csv_file_path = "../outputs/annotations/coral_annotated_breastca_21.csv"

    valid_types = [
        "Symptom",
        "ClinicalCondition",
        "Allergy",
        "PerformanceStatus",
        "GenomicTest",
        "Pathology",
        "Radiology",
        "DiagnosticLabTest",
        "RadPathResult",
        "GenomicTestResult",
        "LabTestResult",
        "Histology",
        "Metastasis",
        "LymphNodeInvolvement",
        "Stage",
        "TNM",
        "Grade",
        "LocalInvasion",
        "BiomarkerName",
        "ProcedureName",
        "ProcedureModifier",
        "ProcedureOutcome",
        "MarginStatus",
        "MedicationName",
        "MedicationRegimen",
        "MedicationModifier",
        "Cycles",
        "RadiationTherapyName",
        "RadiationTherapyModifier",
        "TreatmentDosage",
        "TreatmentDoseModification",
        "TreatmentType",
        "ClinicalTrial",
        "DiseaseState",
        "UnspecifiedEntity"
    ]

    try:
        convert_ann_to_csv(ann_file_path, csv_file_path, valid_types)
        print(f"转换完成！输出文件：{csv_file_path}")
    except Exception as e:
        print(f"转换过程中出现错误：{str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
