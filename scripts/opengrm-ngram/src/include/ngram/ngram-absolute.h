// ngram-absolute.h
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
// Copyright 2009-2013 Brian Roark and Google, Inc.
// Authors: roarkbr@gmail.com  (Brian Roark)
//          allauzen@google.com (Cyril Allauzen)
//          riley@google.com (Michael Riley)
//
// \file
// Absolute Discounting derived class for smoothing

#ifndef NGRAM_NGRAM_ABSOLUTE_H__
#define NGRAM_NGRAM_ABSOLUTE_H__

#include <vector>

#include<ngram/ngram-count-of-counts.h>
#include<ngram/ngram-make.h>

namespace ngram {

class NGramAbsolute : public NGramMake {
 public:
  // Construct NGramMake object, consisting of the FST and some
  // information about the states under the assumption that the FST is a model.
  // Ownership of the FST is retained by the caller.
  NGramAbsolute(StdMutableFst *infst,
		bool backoff = false, Label backoff_label = 0,
		double norm_eps = kNormEps, bool check_consistency = false,
		double parameter = -1.0, int bins = -1)
    : NGramMake(infst, backoff, backoff_label, norm_eps, check_consistency),
      parameter_(parameter),
      bins_(bins <= 0 ? 1 : bins),
      count_of_counts_(bins_) {
  }

  // Smooth model according to 'method' and parameters.
  void MakeNGramModel();

  // Pass in count of counts (rather than computing them)
  void SetCountOfCounts(const StdFst &fst) { count_of_counts_.SetCounts(fst); }

 protected:
  // Return negative log discounted count for provided negative log count
  double GetDiscount(double neglogcount, int order) const;

 private:
  // Calculate absolute discount parameter for count i
  // Note: discounts stored with bin indices starting at 0, bin k is count k+1
  void CalculateAbsoluteDiscount(int order, int bin) {
    if (parameter_ >= 0) {  // user provided discount parameter
      discount_[order][bin] = parameter_;
    } else {  // no discount parameter given: assign based on rule of thumb
      double ROTval = AbsDiscountRuleOfThumb(order);
      if (ROTval <= 0.0) {  // rule of thumb provides unusable parameter
	discount_[order][bin] = 0.6;  // just assign some default parameter
      } else {  // assign according to formula for given rule of thumb value
	discount_[order][bin] = AbsoluteDiscountFormula(order, bin, ROTval);
      }
    }
  }

  // Calculate absolute discounting parameter according to histogram formula.
  // Using Chen and Goodman version from equation (26) of paper
  // For count i, discount: i - ( (i+1) Y n_{i+1} / n_{i} ) for a given Y
  double AbsoluteDiscountFormula(int order, int bin, double Y) {
    double discount = bin + 1, n = bin + 2;  // recall bin (k-1) = count k
    n *= Y * count_of_counts_.Count(order, bin + 1);
    if (n == 0.0) n++;  // to avoid full discounts when given an empty bin
    if (count_of_counts_.Count(order, bin) > 0.0)
      n /= count_of_counts_.Count(order, bin);
    discount -= n;
    if (discount <= 0)
      discount = kNormEps;
    return discount;
  }

  // Generalized rule of thumb: Y = k n_k / ( k n_k + (k+1) * n_{k+1} )
  // where n_k is the total count mass for items that occurred k times
  // Note: method generalized to allow for zeros in low count bins:
  //       find lowest non-empty count bins, then use rule of thumb
  double AbsDiscountRuleOfThumb(int order) {
    int basebin = 1;  // cannot assume bins have observations (count pruning)
    while (basebin <= bins_ &&  // find lowest non-zero pair of bins
	   (count_of_counts_.Count(order, basebin - 1) <= 0.0 ||
	    count_of_counts_.Count(order, basebin) <= 0.0))
      basebin++;
    if (basebin > bins_)  // insufficient non-zero data available in histogram
      return 0.0;
    double k = basebin, kn_k = k * count_of_counts_.Count(order, basebin - 1), 
      kp1n_kp1 = (k + 1) * count_of_counts_.Count(order, basebin);
    return kn_k / (kn_k + kp1n_kp1);
  }

  // Calculate discounts for each order, according to the requested method
  void CalculateDiscounts();

  double parameter_;                     // Absolute Discounting D
  int bins_;                             // number of bins for discounting
  NGramCountOfCounts count_of_counts_;   // count bins for orders
  vector < vector <double> > discount_;  // discount for bins
  DISALLOW_COPY_AND_ASSIGN(NGramAbsolute);
};


}  // namespace ngram

#endif  // NGRAM_NGRAM_ABSOLUTE_H__
