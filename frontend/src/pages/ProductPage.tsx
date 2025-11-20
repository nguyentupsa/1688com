import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'

// Zod schema for 1688 product URL validation
const productFormSchema = z.object({
  productUrl: z.string()
    .min(1, 'Product URL is required')
    .url('Please enter a valid URL')
    .refine(
      (url: string) => url.includes('1688.com'),
      { message: 'URL must be from 1688.com' }
    ),
  openingMessage: z.string().optional(),
})

type ProductFormData = z.infer<typeof productFormSchema>

export const ProductPage = () => {
  // React Hook Form for product configuration
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    reset
  } = useForm<ProductFormData>({
    resolver: zodResolver(productFormSchema),
    defaultValues: {
      productUrl: 'https://detail.1688.com/offer/8213687943598.html',
      openingMessage: '你好，我对这款产品感兴趣。请问最小起订量、单价（含税/不含税）、运费、交货期是多少？支持定制和开增票吗？谢谢！'
    }
  })

  
  // Handle product form submission
  const onProductSubmit = (data: ProductFormData) => {
    console.log('Starting negotiation with:', data)
    // TODO: Integrate with backend negotiation API
  }

  
  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">1688 Product Negotiation</h1>

        {/* Product Configuration Form */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-xl font-semibold text-gray-800 mb-6">Product Configuration</h2>

          <form onSubmit={handleSubmit(onProductSubmit)} className="space-y-6">
            {/* 1688 Product URL */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                1688 Product URL
              </label>
              <input
                type="url"
                {...register('productUrl')}
                placeholder="https://detail.1688.com/offer/xxxxxxxx.html"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                disabled={isSubmitting}
              />
              {errors.productUrl && (
                <p className="mt-1 text-sm text-red-600">{errors.productUrl.message}</p>
              )}
            </div>

  
            {/* Opening Message */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Opening Message
              </label>
              <textarea
                {...register('openingMessage')}
                rows={4}
                placeholder="Enter your opening message..."
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                disabled={isSubmitting}
              />
              {errors.openingMessage && (
                <p className="mt-1 text-sm text-red-600">{errors.openingMessage.message}</p>
              )}
            </div>

            {/* Submit Button */}
            <div className="flex space-x-4">
              <button
                type="submit"
                disabled={isSubmitting}
                className="px-6 py-3 bg-green-600 text-white rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isSubmitting ? 'Starting...' : 'Start Negotiation'}
              </button>

              <button
                type="button"
                onClick={() => reset()}
                disabled={isSubmitting}
                className="px-6 py-3 bg-gray-600 text-white rounded-md hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Reset Form
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}

export default ProductPage